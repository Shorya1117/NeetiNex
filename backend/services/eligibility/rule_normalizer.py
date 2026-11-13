"""
Rule normalizer: validates dataset rules and normalizes user values so
the evaluator can compare them safely.

Dataset content is UNTRUSTED data: rules are only ever interpreted through
the operator registry in rule_evaluator.py - never executed.
"""

from typing import Any, Dict, Optional

from backend.services.eligibility.field_catalog import field_label

# Result statuses
PASS, FAIL, UNKNOWN, NOT_APPLICABLE = "PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"
# Why a status is UNKNOWN
MISSING_INFO, MANUAL_REVIEW, CONFLICT, MALFORMED = (
    "MISSING_INFO", "MANUAL_REVIEW", "CONFLICT", "MALFORMED_RULE")

LOGIC_OPERATORS = {"AND", "OR", "NOT"}


def normalize_value(value: Any) -> Any:
    """Case/space-insensitive form of a value, used for comparisons."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return " ".join(value.strip().lower().replace("_", " ").split())
    if isinstance(value, (list, tuple)):
        return [normalize_value(v) for v in value]
    return value


def normalize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Drop empty values; keep everything else as given (already validated)."""
    return {k: v for k, v in profile.items() if v is not None and v != ""}


def is_group(node: Dict[str, Any]) -> bool:
    return isinstance(node, dict) and "logic" in node and "rules" in node


def validate_rule(rule: Any) -> Optional[str]:
    """Return None if the rule is well-formed, else a short problem string."""
    if not isinstance(rule, dict):
        return "rule is not an object"
    kind = rule.get("kind", "condition")
    if kind != "condition":
        return None
    for key in ("field", "operator"):
        if not rule.get(key):
            return f"missing '{key}'"
    if rule["operator"] != "EXISTS" and "value" not in rule:
        return "missing 'value'"
    return None


def rule_label(rule: Dict[str, Any]) -> str:
    return rule.get("label") or field_label(rule.get("field", "condition"))
