"""
Comparison service: builds the side-by-side table the chat shows.

For every candidate scheme it runs the rule engine (never an LLM) and keeps:
  scheme | your matching conditions | status | other conditions to verify |
  where to apply | documents required | official source
"""

import re
from typing import Any, Dict, List, Optional

from backend.services.eligibility.eligibility_service import EligibilityService
from backend.services.eligibility.scheme_finder import pretty_department

STATUS_RANK = {"ELIGIBLE": 0, "UNVERIFIED": 1, "NEED_MORE_INFORMATION": 2}
STATUS_LABEL = {
    "ELIGIBLE": "Eligible (all conditions met)",
    "UNVERIFIED": "Likely eligible - verify the extra conditions",
    "NEED_MORE_INFORMATION": "More details needed",
}
URL = re.compile(r"https?://[^\s,;)]+")


def split_application(text: str) -> Dict[str, Any]:
    """'Contact e-mitra. 2. Login at SSO ... 3. https://...' -> steps + urls."""
    urls = list(dict.fromkeys(URL.findall(text or "")))
    cleaned = URL.sub("", text or "")
    steps = [s.strip(" .,;") for s in re.split(r"(?:^|\s)\d{1,2}\.\s+", cleaned) if s.strip(" .,;")]
    return {"steps": steps[:4], "urls": urls[:2]}


def _clean_steps(steps: List[str]) -> List[str]:
    return [x for x in steps if x.strip().upper() not in ("N/A", "NA", "NONE")]


def _short(text: str, limit: int = 170) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_row(service: EligibilityService, scheme: Dict[str, Any],
              profile: Dict[str, Any]) -> Dict[str, Any]:
    result = service.evaluate(scheme, profile)
    apply = split_application(scheme.get("application_process", ""))
    apply["steps"] = _clean_steps(apply["steps"])
    src = scheme.get("source", {})
    matched = [f"{c['label']}: {c['provided_display']} (needs {c['required_display']})"
               for c in result["matched_conditions"]]
    status = result["overall_status"]
    label = STATUS_LABEL.get(status, status)
    if status == "UNVERIFIED" and not matched:
        label = "Cannot be auto-checked - read the conditions"
    return {
        "scheme_id": scheme["scheme_id"],
        "scheme_name": scheme["scheme_name"],
        "department": pretty_department(scheme.get("department")),
        "status": result["overall_status"],
        "status_label": label,
        "your_match": matched,
        "not_met": [f"{c['label']}: {c['provided_display']} (needs {c['required_display']})"
                    for c in result["failed_conditions"]],
        "need_to_tell": [m["label"] for m in result["missing_information"]],
        "other_conditions": [_short(m["text"]) for m in result["manual_checks"]][:4],
        "other_conditions_total": len(result["manual_checks"]),
        "where_to_apply": apply["steps"],
        "apply_links": apply["urls"],
        "documents": [d.strip(" .") for d in scheme.get("documents_required", [])][:8],
        "source_url": src.get("source_url"),
        "verification_status": src.get("verification_status", "extracted_unverified"),
        "topic_score": scheme.get("_topic_score", 0),
    }


HIGHER_ED = re.compile(
    r"\b(college|higher education|graduat\w*|post.?graduat\w*|post.?matric|iit|iim|"
    r"universit\w*|diploma|degree|ug|pg|fellowship|ph\.?d|research)\b", re.I)
SCHOOL_LEVEL = re.compile(r"\bclass(?:es)?\s*\d|pre.?matric|\bschool\b", re.I)


def education_level_mismatch(scheme: Dict[str, Any], profile: Dict[str, Any]) -> Optional[str]:
    """School student (class <= 12) vs a college/university-level scheme.
    Keyword based on the scheme's own text, so it is shown as a reason, not hidden."""
    cls = profile.get("current_class")
    if not cls or cls > 12:
        return None
    text = scheme["scheme_name"] + " " + (scheme.get("original_eligibility_text") or "")
    higher_dept = "higher" in (scheme.get("department") or "").lower()
    if (higher_dept or HIGHER_ED.search(text)) and not SCHOOL_LEVEL.search(text):
        return (f"Not applicable at your education level: this is a college/university-level "
                f"scheme and you are in class {cls}")
    return None


def build_comparison(service: EligibilityService, candidates: List[Dict[str, Any]],
                     profile: Dict[str, Any], max_rows: int = 12) -> Dict[str, Any]:
    rows, excluded = [], []
    for scheme in candidates:
        mismatch = education_level_mismatch(scheme, profile)
        if mismatch:
            excluded.append({"scheme_name": scheme["scheme_name"], "reason": mismatch})
            continue
        row = build_row(service, scheme, profile)
        if row["status"] == "NOT_ELIGIBLE":
            excluded.append({"scheme_name": row["scheme_name"], "reason": "; ".join(row["not_met"])})
        else:
            rows.append(row)

    def rank(r):
        # confirmed matches first, then relevance to the topic + number of matched conditions
        unchecked = r["status"] == "UNVERIFIED" and not r["your_match"]
        group = 3 if unchecked else STATUS_RANK.get(r["status"], 9)
        # topic relevance first (what the user asked for), then confirmed matches
        return (group, -r["topic_score"], -len(r["your_match"]), r["scheme_name"])

    rows.sort(key=rank)

    # which missing details would help most (for the follow-up question)
    freq: Dict[str, int] = {}
    for r in rows:
        for label in r["need_to_tell"]:
            freq[label] = freq.get(label, 0) + 1
    ask_next = [k for k, _ in sorted(freq.items(), key=lambda kv: -kv[1])][:4]

    counts = {"ELIGIBLE": 0, "UNVERIFIED": 0, "NEED_MORE_INFORMATION": 0}
    counts["UNCHECKABLE"] = 0
    for r in rows:
        key = "UNCHECKABLE" if (r["status"] == "UNVERIFIED" and not r["your_match"]) else r["status"]
        counts[key] = counts.get(key, 0) + 1
    return {
        "rows": rows[:max_rows],
        "total_matching": len(rows),
        "counts": counts,
        "not_eligible_count": len(excluded),
        "not_eligible": excluded[:8],
        "ask_next": ask_next,
        "candidates_checked": len(candidates),
    }
