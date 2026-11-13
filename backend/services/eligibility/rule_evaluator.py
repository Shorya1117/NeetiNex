"""
Rule evaluator: evaluates ONE rule against a user profile.

Only responsibility: rule + profile -> PASS / FAIL / UNKNOWN / NOT_APPLICABLE.
Operators live in a controlled registry (no eval(), no dynamic code).
Dataset rules never contain scheme-specific Python - only data.
"""

import logging
from typing import Any, Callable, Dict

from backend.services.eligibility.rule_normalizer import (
    CONFLICT, FAIL, MALFORMED, MANUAL_REVIEW, MISSING_INFO, NOT_APPLICABLE, PASS,
    UNKNOWN, normalize_value, rule_label, validate_rule,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Operator registry: name -> fn(provided, required) -> bool
# To add an operator, add ONE entry here.
# ----------------------------------------------------------------------
def _between(p: Any, r: Any) -> bool:
    low, high = r
    return low <= p <= high


OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    "EQUALS": lambda p, r: normalize_value(p) == normalize_value(r),
    "NOT_EQUALS": lambda p, r: normalize_value(p) != normalize_value(r),
    "GREATER_THAN": lambda p, r: p > r,
    "GREATER_THAN_OR_EQUAL": lambda p, r: p >= r,
    "LESS_THAN": lambda p, r: p < r,
    "LESS_THAN_OR_EQUAL": lambda p, r: p <= r,
    "IN": lambda p, r: normalize_value(p) in normalize_value(list(r)),
    "NOT_IN": lambda p, r: normalize_value(p) not in normalize_value(list(r)),
    "BETWEEN": _between,
    "CONTAINS": lambda p, r: normalize_value(r) in (
        normalize_value(p) if isinstance(p, (list, tuple, str)) else []),
    "EXISTS": lambda p, r: p is not None,
}

NUMERIC_OPERATORS = {
    "GREATER_THAN", "GREATER_THAN_OR_EQUAL", "LESS_THAN", "LESS_THAN_OR_EQUAL",
    "BETWEEN",
}


def _result(rule: Dict[str, Any], status: str, provided: Any = None,
            reason_code: str = None) -> Dict[str, Any]:
    return {
        "node_type": "condition",
        "rule_id": rule.get("rule_id", "?"),
        "field": rule.get("field"),
        "label": rule_label(rule),
        "operator": rule.get("operator"),
        "required_value": rule.get("value"),
        "provided_value": provided,
        "status": status,
        "reason_code": reason_code,
        "mandatory": bool(rule.get("mandatory", True)),
        "source_text": rule.get("source_text"),
        "verification_status": rule.get("verification_status", "extracted_unverified"),
        "kind": rule.get("kind", "condition"),
        "manual_kind": rule.get("manual_kind"),
        "manual_reason": rule.get("reason"),
    }


def evaluate_rule(rule: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single (leaf) rule."""
    problem = validate_rule(rule)
    if problem:
        logger.warning("Malformed rule %s: %s", rule.get("rule_id") if
                       isinstance(rule, dict) else "?", problem)
        return _result(rule if isinstance(rule, dict) else {}, UNKNOWN,
                       reason_code=MALFORMED)

    kind = rule.get("kind", "condition")
    if kind == "informational":
        return _result(rule, NOT_APPLICABLE)
    if kind == "manual":
        # A criterion we could not structure: never assume it is satisfied.
        return _result(rule, UNKNOWN, reason_code=MANUAL_REVIEW)
    if rule.get("conflict"):
        provided = profile.get(rule["field"])
        return _result(rule, UNKNOWN, provided, reason_code=CONFLICT)

    operator = rule["operator"]
    fn = OPERATORS.get(operator)
    if fn is None:
        logger.warning("Unknown operator %s in rule %s", operator, rule.get("rule_id"))
        return _result(rule, UNKNOWN, reason_code=MALFORMED)

    provided = profile.get(rule["field"])
    if provided is None and operator != "EXISTS":
        return _result(rule, UNKNOWN, None, reason_code=MISSING_INFO)

    try:
        if operator in NUMERIC_OPERATORS and isinstance(provided, bool):
            raise TypeError("boolean is not numeric")
        passed = fn(provided, rule.get("value"))
    except (TypeError, ValueError):
        logger.warning("Type mismatch evaluating rule %s", rule.get("rule_id"))
        return _result(rule, UNKNOWN, provided, reason_code=MALFORMED)

    return _result(rule, PASS if passed else FAIL, provided)
