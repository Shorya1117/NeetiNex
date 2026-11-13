"""
Eligibility service: the single entry point used by the API router.

profile + scheme_id  ->  evaluation  ->  aggregation  ->  explanation
"""

import logging
from typing import Any, Dict, List, Optional

from backend.services.eligibility.dataset_service import (
    DatasetService, SchemeNotFoundError, dataset_service, iter_leaf_rules,
    required_fields,
)
from backend.services.eligibility.explanation_service import (
    explain_condition, explain_overall, format_required, format_value,
)
from backend.services.eligibility.field_catalog import get_field_meta
from backend.services.eligibility.result_aggregator import aggregate_status
from backend.services.eligibility.rule_engine import evaluate_conditions, flatten_leaves
from backend.services.eligibility.rule_normalizer import (
    FAIL, MISSING_INFO, NOT_APPLICABLE, PASS, UNKNOWN, normalize_profile,
)

logger = logging.getLogger(__name__)

STATUS_ORDER = {"ELIGIBLE": 0, "UNVERIFIED": 1, "NEED_MORE_INFORMATION": 2,
                "NOT_ELIGIBLE": 3}


class EligibilityService:
    def __init__(self, dataset: Optional[DatasetService] = None):
        self.dataset = dataset or dataset_service

    # ------------------------------------------------------------------
    @staticmethod
    def _field_descriptor(field: str, why: str) -> Dict[str, Any]:
        meta = get_field_meta(field)
        return {
            "field": field, "label": meta["label"], "type": meta["type"],
            "why_required": why, "options": meta.get("options"),
            "unit": meta.get("unit"), "help": meta.get("help"),
        }

    @staticmethod
    def _source_refs(scheme: Dict[str, Any]) -> List[Dict[str, Any]]:
        src = scheme.get("source", {})
        return [{
            "source_url": src.get("source_url"),
            "source_document": src.get("source_document"),
            "verification_status": src.get("verification_status", "extracted_unverified"),
        }]

    @staticmethod
    def _condition_view(leaf: Dict[str, Any]) -> Dict[str, Any]:
        field = leaf.get("field") or ""
        view = {
            "rule_id": leaf["rule_id"], "field": leaf.get("field"),
            "label": leaf["label"], "operator": leaf.get("operator"),
            "required_value": leaf.get("required_value"),
            "provided_value": leaf.get("provided_value"),
            "required_display": (format_required(field, leaf["operator"],
                                                 leaf["required_value"])
                                 if leaf.get("operator") else ""),
            "provided_display": (format_value(field, leaf.get("provided_value"))
                                 if leaf.get("provided_value") is not None else "Not provided"),
            "status": leaf["status"], "reason_code": leaf.get("reason_code"),
            "mandatory": leaf["mandatory"], "source_text": leaf.get("source_text"),
            "verification_status": leaf["verification_status"],
        }
        view["explanation"] = explain_condition({**leaf, **view})
        return view

    # ------------------------------------------------------------------
    def evaluate(self, scheme: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        profile = normalize_profile(profile)
        tree = evaluate_conditions(scheme["conditions"], profile)
        top_nodes = tree["children"]
        status = aggregate_status(top_nodes)
        leaves = flatten_leaves(tree)

        conditions = [l for l in leaves if l.get("kind", "condition") == "condition"]
        manual = [l for l in leaves if l.get("kind") == "manual"]
        views = [self._condition_view(l) for l in conditions]

        matched = [v for v in views if v["status"] == PASS]
        failed = [v for v in views if v["status"] == FAIL and v["mandatory"]]
        unknown = [v for v in views if v["status"] == UNKNOWN]

        missing, seen = [], set()
        for v in unknown:
            if v["reason_code"] == MISSING_INFO and v["field"] not in seen:
                seen.add(v["field"])
                missing.append(self._field_descriptor(
                    v["field"], v["source_text"] or ""))

        manual_checks = [{
            "text": m.get("source_text") or "", "kind": m.get("manual_kind") or "unparsed",
            "reason": m.get("manual_reason") or "",
        } for m in manual]

        src = scheme.get("source", {})
        return {
            "scheme_id": scheme["scheme_id"],
            "scheme_name": scheme["scheme_name"],
            "department": scheme.get("department"),
            "overall_status": status,
            "eligible": status == "ELIGIBLE",
            "matched_conditions": matched,
            "failed_conditions": failed,
            "unknown_conditions": unknown,
            "missing_information": missing,
            "manual_checks": manual_checks,
            "explanation": explain_overall(
                status, scheme["scheme_name"], len(matched), len(failed),
                len(missing), len(manual_checks)),
            "verification_status": src.get("verification_status", "extracted_unverified"),
            "source_references": self._source_refs(scheme),
            "documents_required": scheme.get("documents_required", []),
        }

    # ------------------------------------------------------------------
    # Public operations used by the router
    # ------------------------------------------------------------------
    def check(self, scheme_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        scheme = self.dataset.get(scheme_id)
        result = self.evaluate(scheme, profile)
        logger.info("eligibility check scheme=%s status=%s", scheme_id,
                    result["overall_status"])  # never log profile values
        return result

    def check_multiple(self, profile: Dict[str, Any],
                       scheme_ids: Optional[List[str]] = None,
                       departments: Optional[List[str]] = None,
                       statuses: Optional[List[str]] = None,
                       limit: Optional[int] = None) -> Dict[str, Any]:
        schemes = ([self.dataset.get(sid) for sid in scheme_ids]
                   if scheme_ids else self.dataset.all())
        if departments:
            wanted = {d.lower() for d in departments}
            schemes = [s for s in schemes if (s.get("department") or "").lower() in wanted]

        results, counts = [], {k: 0 for k in STATUS_ORDER}
        for scheme in schemes:
            r = self.evaluate(scheme, profile)
            counts[r["overall_status"]] += 1
            if statuses and r["overall_status"] not in statuses:
                continue
            results.append({
                "scheme_id": r["scheme_id"], "scheme_name": r["scheme_name"],
                "department": r["department"], "overall_status": r["overall_status"],
                "eligible": r["eligible"],
                "matched_conditions": r["matched_conditions"],
                "failed_conditions": r["failed_conditions"],
                "missing_information": r["missing_information"],
                "manual_check_count": len(r["manual_checks"]),
                "verification_status": r["verification_status"],
                "source_references": r["source_references"],
            })
        results.sort(key=lambda r: (STATUS_ORDER[r["overall_status"]],
                                    r["scheme_name"].lower()))
        if limit:
            results = results[:limit]
        return {"total_schemes_evaluated": len(schemes), "counts": counts,
                "results": results}

    def get_criteria(self, scheme_id: str) -> Dict[str, Any]:
        scheme = self.dataset.get(scheme_id)
        manual = [{
            "text": r.get("source_text", ""), "kind": r.get("manual_kind", "unparsed"),
            "reason": r.get("reason", ""),
        } for r in iter_leaf_rules(scheme["conditions"]) if r.get("kind") == "manual"]
        src = scheme.get("source", {})
        return {
            "scheme_id": scheme["scheme_id"], "scheme_name": scheme["scheme_name"],
            "department": scheme.get("department"),
            "eligibility_status": scheme["eligibility_status"],
            "verification_status": src.get("verification_status", "extracted_unverified"),
            "requirements": scheme.get("eligibility", {}),
            "conditions": scheme["conditions"],
            "required_fields": [self._field_descriptor(f, w)
                                for f, w in required_fields(scheme).items()],
            "manual_checks": manual,
            "exclusions": scheme.get("exclusions", []),
            "original_eligibility_text": scheme.get("original_eligibility_text", ""),
            "documents_required": scheme.get("documents_required", []),
            "source_references": self._source_refs(scheme),
        }

    def missing_information(self, scheme_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        scheme = self.dataset.get(scheme_id)
        profile = normalize_profile(profile)
        needed = required_fields(scheme)
        descriptors = [self._field_descriptor(f, w) for f, w in needed.items()]
        return {
            "scheme_id": scheme["scheme_id"], "scheme_name": scheme["scheme_name"],
            "required_fields": descriptors,
            "missing_fields": [d for d in descriptors if d["field"] not in profile],
        }

    def list_schemes(self) -> List[Dict[str, Any]]:
        out = []
        for s in self.dataset.all():
            leaves = list(iter_leaf_rules(s["conditions"]))
            out.append({
                "scheme_id": s["scheme_id"], "scheme_name": s["scheme_name"],
                "department": s.get("department"),
                "eligibility_status": s["eligibility_status"],
                "auto_checkable_conditions": sum(
                    1 for r in leaves if r.get("kind", "condition") == "condition"),
                "manual_review_items": sum(1 for r in leaves if r.get("kind") == "manual"),
                "required_fields": list(required_fields(s).keys()),
            })
        return sorted(out, key=lambda x: x["scheme_name"].lower())


eligibility_service = EligibilityService()
