"""
Explanation service: builds human-readable text FROM the evaluation result.
It never changes a status - it only describes it (no LLM involved).
"""

from typing import Any, Dict, List

from backend.services.eligibility.field_catalog import field_label
from backend.services.eligibility.result_aggregator import (
    ELIGIBLE, NEED_MORE_INFORMATION, NOT_ELIGIBLE, UNVERIFIED,
)
from backend.services.eligibility.rule_normalizer import (
    CONFLICT, FAIL, MALFORMED, MANUAL_REVIEW, MISSING_INFO, NOT_APPLICABLE, PASS,
)

INCOME_FIELDS = {"annual_income", "annual_family_income",
                 "annual_personal_income", "annual_parent_income"}


def indian_rupees(amount: float) -> str:
    """180000 -> ₹1,80,000 (Indian digit grouping)."""
    s = str(int(round(amount)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return "₹" + s


def format_value(field: str, value: Any) -> str:
    if value is None:
        return "Not provided"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple)):
        return " / ".join(format_value(field, v) for v in value)
    if field in INCOME_FIELDS and isinstance(value, (int, float)):
        return indian_rupees(value)
    if field == "age":
        return f"{value:g} years" if isinstance(value, float) else f"{value} years"
    if field == "disability_percentage":
        return f"{value:g}%"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("_", " ")


_PHRASES = {
    "EQUALS": "{v}", "NOT_EQUALS": "anything except {v}",
    "GREATER_THAN": "more than {v}", "GREATER_THAN_OR_EQUAL": "at least {v}",
    "LESS_THAN": "less than {v}", "LESS_THAN_OR_EQUAL": "up to {v}",
    "IN": "one of: {v}", "NOT_IN": "none of: {v}", "CONTAINS": "includes {v}",
}


def format_required(field: str, operator: str, value: Any) -> str:
    if operator == "BETWEEN" and isinstance(value, (list, tuple)) and len(value) == 2:
        if field == "age":
            return f"{value[0]}–{value[1]} years"
        return f"{format_value(field, value[0])} to {format_value(field, value[1])}"
    if operator == "EXISTS":
        return "must be provided"
    template = _PHRASES.get(operator, "{v}")
    return template.format(v=format_value(field, value))


def explain_condition(r: Dict[str, Any]) -> str:
    """One-sentence explanation of a leaf result."""
    status, reason = r["status"], r.get("reason_code")
    field = r.get("field") or ""
    label = r["label"]
    req = r.get("required_display", "")
    got = r.get("provided_display", "")
    op = r.get("operator")

    if r.get("kind") == "manual":
        return ("This condition cannot be checked automatically. Please read it "
                "on the official source and confirm it yourself.")
    if status == NOT_APPLICABLE:
        return "Informational statement - not used for the decision."
    if reason == MISSING_INFO:
        return f"{label} was not provided, so this condition could not be checked."
    if reason == CONFLICT:
        return ("The source text gives conflicting values for this condition, "
                "so it needs manual verification.")
    if reason == MALFORMED:
        return "This criterion could not be evaluated reliably."
    if status == PASS:
        return f"{label} ({got}) meets the requirement ({req})."
    if status == FAIL:
        if field in INCOME_FIELDS and op in ("LESS_THAN", "LESS_THAN_OR_EQUAL"):
            return f"Your {label.lower()} ({got}) exceeds the specified limit ({req})."
        if field == "age" and op in ("GREATER_THAN", "GREATER_THAN_OR_EQUAL"):
            return f"Your age ({got}) is below the minimum age requirement ({req})."
        if field == "age" and op in ("LESS_THAN", "LESS_THAN_OR_EQUAL"):
            return f"Your age ({got}) is above the maximum age limit ({req})."
        if field == "age" and op == "BETWEEN":
            return f"Your age ({got}) is outside the required range ({req})."
        return f"{label} ({got}) does not meet the requirement ({req})."
    return ""


def explain_overall(status: str, scheme_name: str, n_pass: int, n_fail: int,
                    n_missing: int, n_manual: int) -> str:
    if status == ELIGIBLE:
        return (f"Based on the criteria available for {scheme_name}, you satisfy all "
                f"{n_pass} checkable mandatory condition(s).")
    if status == NOT_ELIGIBLE:
        return (f"You do not meet {n_fail} mandatory condition(s) of {scheme_name}, "
                "so you are not eligible as per the available criteria.")
    if status == NEED_MORE_INFORMATION:
        return (f"No mandatory condition has failed so far, but {n_missing} detail(s) "
                "are still needed before eligibility can be decided.")
    if status == UNVERIFIED:
        if n_manual:
            return (f"A confirmed decision is not possible: {n_manual} criterion/criteria "
                    f"of {scheme_name} could not be checked automatically and need "
                    "manual verification on the official source.")
        return f"Eligibility criteria for {scheme_name} are not available in structured form."
    return ""
