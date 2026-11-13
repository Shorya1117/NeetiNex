"""
ONE-STEP eligibility dataset builder.

    python -m backend.ingestion.eligibility_structuring.build_eligibility_dataset

Reads the existing Chroma vector store -> rebuilds each scheme's eligibility
text -> extracts structured rules -> writes:

    backend/data/eligibility/eligibility_dataset.json
    backend/data/eligibility/dataset_validation_report.json

Nothing is invented: lines that cannot be structured are kept as MANUAL
rules with their original text. Every scheme is preserved.

Optional human verification: put reviewed schemes in
backend/data/eligibility/verified_overrides.json (see README section in the
printed help) and re-run - those schemes get verification_status "verified".
"""

import argparse
import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from backend.ingestion.eligibility_structuring.chroma_reader import (
    read_chunks, rebuild_schemes,
)
from backend.ingestion.eligibility_structuring.rule_extractor import (
    is_enumerated_item, process_line,
)
from backend.services.eligibility.field_catalog import FIELD_CATALOG

logger = logging.getLogger("eligibility_builder")

BACKEND_DIR = Path(__file__).resolve().parents[2]
VECTORSTORE_DIR = BACKEND_DIR / "data" / "vectorstore"
OUTPUT_DIR = BACKEND_DIR / "data" / "eligibility"
DATASET_FILE = OUTPUT_DIR / "eligibility_dataset.json"
REPORT_FILE = OUTPUT_DIR / "dataset_validation_report.json"
OVERRIDES_FILE = OUTPUT_DIR / "verified_overrides.json"

SCHEMA_VERSION = "1.0"
KNOWN_OPERATORS = {
    "EQUALS", "NOT_EQUALS", "GREATER_THAN", "GREATER_THAN_OR_EQUAL",
    "LESS_THAN", "LESS_THAN_OR_EQUAL", "IN", "NOT_IN", "BETWEEN",
    "CONTAINS", "EXISTS",
}


# ----------------------------------------------------------------------
# Text -> lines
# ----------------------------------------------------------------------

def split_eligibility_lines(text: str) -> List[str]:
    """One condition per line; exact duplicates inside a scheme removed."""
    seen, lines = set(), []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        # Some source lines repeat the same sentence twice back to back
        half = len(line) // 2
        if len(line) > 40 and line[:half].strip() == line[half:].strip():
            line = line[:half].strip()
        key = re.sub(r"\W+", "", line.lower())
        if key and key not in seen:
            seen.add(key)
            lines.append(line)
    return lines


# ----------------------------------------------------------------------
# Scheme -> record
# ----------------------------------------------------------------------

def build_rules(lines: List[str], scheme_id: str) -> List[Dict[str, Any]]:
    enum_count = sum(1 for ln in lines if is_enumerated_item(ln))
    rules: List[Dict[str, Any]] = []
    for line in lines:
        enumerated = enum_count >= 2 and is_enumerated_item(line)
        rules.extend(process_line(line, enumerated=enumerated))

    # Drop exact duplicate conditions (same field/operator/value)
    unique, seen = [], set()
    for r in rules:
        if r["kind"] == "condition":
            key = (r["field"], r["operator"], json.dumps(r["value"]))
            if key in seen:
                continue
            seen.add(key)
        unique.append(r)

    # Same field + same operator but different value -> conflicting sources
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in unique:
        if r["kind"] == "condition":
            groups.setdefault((r["field"], r["operator"]), []).append(r)
    for rs in groups.values():
        if len(rs) > 1:
            for r in rs:
                r["conflict"] = True

    for i, r in enumerate(unique, start=1):
        r["rule_id"] = f"{scheme_id}-R{i}"
    return unique


def summarise(rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Flat per-field view for humans: {field: [{operator, value}]}."""
    out: Dict[str, Any] = {}
    for r in rules:
        if r["kind"] == "condition":
            out.setdefault(r["field"], []).append(
                {"operator": r["operator"], "value": r["value"]})
    return out


def structuring_status(rules: List[Dict[str, Any]]) -> str:
    conditions = [r for r in rules if r["kind"] == "condition"]
    manual = [r for r in rules if r["kind"] == "manual"]
    if not conditions:
        return "unstructured"
    return "partially_structured" if manual else "fully_structured"


def build_record(scheme: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    scheme_id = scheme["scheme_id"]
    sections = scheme["sections"]
    eligibility_text = sections.get("eligibility", "")
    lines = split_eligibility_lines(eligibility_text)
    rules = build_rules(lines, scheme_id)

    docs = [ln.strip() for ln in sections.get("documents_required", "").split("\n")
            if ln.strip() and ln.strip().upper() != "N/A"]

    url = scheme.get("source_url")
    record = {
        "scheme_id": scheme_id,
        "scheme_name": scheme["scheme_name"],
        "department": scheme.get("department"),
        "eligibility_status": structuring_status(rules),
        "eligibility": summarise(rules),
        "conditions": {"logic": "AND", "rules": rules},
        "exclusions": [r["source_text"] for r in rules
                       if r["kind"] == "manual" and r["manual_kind"] == "exclusion"],
        "documents_required": docs,
        "application_process": sections.get("application_process", "").strip(),
        "original_eligibility_text": eligibility_text,
        "source": {
            "source_url": url,
            "source_portal": urlparse(url).netloc if url else None,
            "source_document": "Rajasthan Jan Soochna scheme eligibility page"
                               if scheme.get("source_type") == "jansoochna_eligibility"
                               else scheme.get("source_type"),
            "source_file": scheme.get("source_file"),
            "verification_status": "extracted_unverified",
        },
        "last_verified": None,
    }

    override = overrides.get(scheme_id)
    if override and override.get("verified") is True:
        record["source"]["verification_status"] = "verified"
        record["source"]["verified_by"] = override.get("reviewer")
        record["source"]["source_document"] = override.get(
            "source_document", record["source"]["source_document"])
        record["last_verified"] = override.get("last_verified")
        for r in rules:
            if r["kind"] == "condition":
                r["verification_status"] = "verified"
    return record


# ----------------------------------------------------------------------
# Validation + quality report
# ----------------------------------------------------------------------

def validate_record(rec: Dict[str, Any]) -> List[str]:
    issues = []
    if not rec.get("scheme_name"):
        issues.append("missing scheme_name")
    if not rec["source"].get("source_url"):
        issues.append("missing source_url")
    if not rec["original_eligibility_text"].strip():
        issues.append("empty eligibility text")
    for r in rec["conditions"]["rules"]:
        if r["kind"] == "condition":
            if r["operator"] not in KNOWN_OPERATORS:
                issues.append(f"{r['rule_id']}: unknown operator {r['operator']}")
            if r["field"] not in FIELD_CATALOG:
                issues.append(f"{r['rule_id']}: field {r['field']} not in catalog")
            if r.get("conflict"):
                issues.append(f"{r['rule_id']}: conflicting values for "
                              f"{r['field']} {r['operator']}")
    return issues


def build_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(records)
    field_counter: Counter = Counter()
    status_counter: Counter = Counter()
    manual_kinds: Counter = Counter()
    issues: Dict[str, List[str]] = {}
    lines_parsed = lines_manual = lines_info = 0

    for rec in records:
        status_counter[rec["eligibility_status"]] += 1
        fields = set()
        for r in rec["conditions"]["rules"]:
            if r["kind"] == "condition":
                fields.add(r["field"])
                lines_parsed += 1
            elif r["kind"] == "manual":
                lines_manual += 1
                manual_kinds[r["manual_kind"]] += 1
            else:
                lines_info += 1
        field_counter.update(fields)
        found = validate_record(rec)
        if found:
            issues[rec["scheme_id"]] = found

    def count(*names):
        return sum(field_counter[n] for n in names)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "data_source": "Chroma collection 'neetinex_schemes' (read-only)",
        "total_schemes_processed": total,
        "schemes_with_eligibility_text": sum(
            1 for r in records if r["original_eligibility_text"].strip()),
        "structuring_status": dict(status_counter),
        "schemes_requiring_manual_review": sum(
            1 for r in records
            if r["eligibility_status"] in ("partially_structured", "unstructured")),
        "schemes_with_verified_source": sum(
            1 for r in records
            if r["source"]["verification_status"] == "verified"),
        "schemes_with_conflicting_rules": sum(
            1 for r in records
            if any(r_.get("conflict") for r_ in r["conditions"]["rules"])),
        "coverage_by_field": {
            "age": field_counter["age"],
            "income_any": count("annual_income", "annual_family_income",
                                "annual_personal_income", "annual_parent_income"),
            "gender": field_counter["gender"],
            "state": field_counter["state"],
            "category": field_counter["category"],
            "disability": count("disability_status", "disability_percentage"),
            "bpl": field_counter["bpl_status"],
            "occupation": field_counter["occupation"],
            "marital_status": field_counter["marital_status"],
            "education_class": field_counter["current_class"],
            "minority": field_counter["minority_status"],
        },
        "income_type_breakdown": {
            f: field_counter[f] for f in (
                "annual_family_income", "annual_personal_income",
                "annual_parent_income", "annual_income")},
        "eligibility_lines": {
            "auto_structured_rules": lines_parsed,
            "manual_review_lines": lines_manual,
            "informational_lines": lines_info,
            "manual_by_reason": dict(manual_kinds),
        },
        "unstructured_schemes": [
            {"scheme_id": r["scheme_id"], "scheme_name": r["scheme_name"]}
            for r in records if r["eligibility_status"] == "unstructured"],
        "validation_issues": issues,
        "notes": [
            "All schemes are 'extracted_unverified' unless listed in "
            "verified_overrides.json - extraction from a crawler is NOT "
            "official verification.",
            "Missing/unparsed criteria are kept as manual rules; they are "
            "never treated as 'no restriction'.",
        ],
    }


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def load_overrides() -> Dict[str, Any]:
    if OVERRIDES_FILE.exists():
        return json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return {}


def build_dataset(vectorstore_dir: Path = VECTORSTORE_DIR,
                  output_dir: Path = OUTPUT_DIR) -> Dict[str, Any]:
    """Build and write the dataset + report. Returns the report."""
    records_raw = read_chunks(vectorstore_dir)
    schemes = rebuild_schemes(records_raw)
    overrides = load_overrides()

    records = [build_record(s, overrides) for s in
               sorted(schemes.values(), key=lambda s: (s["scheme_name"] or "").lower())]
    report = build_report(records)

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": report["generated_at"],
        "total_schemes": len(records),
        "schemes": records,
    }
    (output_dir / DATASET_FILE.name).write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / REPORT_FILE.name).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = build_dataset()
    print("\n=== Eligibility dataset built ===")
    print(f"Schemes processed        : {report['total_schemes_processed']}")
    print(f"Structuring status       : {report['structuring_status']}")
    print(f"Need manual review       : {report['schemes_requiring_manual_review']}")
    print(f"Coverage by field        : {report['coverage_by_field']}")
    print(f"Lines                    : {report['eligibility_lines']}")
    print(f"Written to               : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
