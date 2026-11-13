"""
Rule engine: coordinates evaluation of a whole condition tree.

  - leaf rules   -> rule_evaluator.evaluate_rule
  - AND / OR / NOT groups (nested) -> three-valued logic here

Three-valued logic (PASS / FAIL / UNKNOWN) keeps "missing information"
different from "failed":
  AND: any FAIL -> FAIL ; else any UNKNOWN -> UNKNOWN ; else PASS
  OR : any PASS -> PASS ; else any UNKNOWN -> UNKNOWN ; else FAIL
  NOT: PASS<->FAIL, UNKNOWN stays UNKNOWN
NOT_APPLICABLE children are ignored.
"""

from typing import Any, Dict, List

from backend.services.eligibility.rule_evaluator import evaluate_rule
from backend.services.eligibility.rule_normalizer import (
    FAIL, MALFORMED, MISSING_INFO, NOT_APPLICABLE, PASS, UNKNOWN, is_group,
)

MAX_DEPTH = 8  # protects against malformed / hostile deeply nested data

# When several UNKNOWNs exist, "missing information" is reported first
# because the user can fix it right away.
_REASON_PRIORITY = [MISSING_INFO, "CONFLICT", "MANUAL_REVIEW", MALFORMED]


def _unknown_reason(children: List[Dict[str, Any]]) -> str:
    reasons = {c.get("reason_code") for c in children if c["status"] == UNKNOWN}
    for reason in _REASON_PRIORITY:
        if reason in reasons:
            return reason
    return MALFORMED


def _combine(logic: str, children: List[Dict[str, Any]]) -> Dict[str, Any]:
    active = [c for c in children if c["status"] != NOT_APPLICABLE]
    statuses = [c["status"] for c in active]
    reason = None

    if not active:
        status = NOT_APPLICABLE
    elif logic == "AND":
        status = FAIL if FAIL in statuses else UNKNOWN if UNKNOWN in statuses else PASS
    elif logic == "OR":
        status = PASS if PASS in statuses else UNKNOWN if UNKNOWN in statuses else FAIL
    elif logic == "NOT":
        child = statuses[0] if len(statuses) == 1 else UNKNOWN
        status = {PASS: FAIL, FAIL: PASS}.get(child, UNKNOWN)
    else:
        status, reason = UNKNOWN, MALFORMED

    if status == UNKNOWN and reason is None:
        reason = _unknown_reason(active)
    return {"status": status, "reason_code": reason}


def evaluate_node(node: Dict[str, Any], profile: Dict[str, Any],
                  depth: int = 0) -> Dict[str, Any]:
    """Evaluate a rule or a (nested) group."""
    if not is_group(node):
        return evaluate_rule(node, profile)

    logic = str(node.get("logic", "")).upper()
    if depth >= MAX_DEPTH or not isinstance(node.get("rules"), list):
        return {"node_type": "group", "logic": logic, "status": UNKNOWN,
                "reason_code": MALFORMED, "mandatory": True, "children": []}

    children = [evaluate_node(child, profile, depth + 1) for child in node["rules"]]
    combined = _combine(logic, children)
    return {
        "node_type": "group", "logic": logic, "children": children,
        "mandatory": bool(node.get("mandatory", True)), **combined,
    }


def flatten_leaves(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """All leaf results of a result tree, in order."""
    if node.get("node_type") != "group":
        return [node]
    leaves: List[Dict[str, Any]] = []
    for child in node["children"]:
        leaves.extend(flatten_leaves(child))
    return leaves


def evaluate_conditions(conditions: Dict[str, Any],
                        profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a scheme's root condition group."""
    return evaluate_node(conditions, profile)
