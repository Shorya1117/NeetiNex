"""Deterministic, three-valued eligibility rule evaluator.

Unknown/missing user attributes never pass a rule. Supported condition nodes:
  {"all": [condition, ...]}
  {"any": [condition, ...]}
  {"not": condition}
  {"attribute": "age", "operator": ">=", "value": 18}
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evaluation:
    status: str  # TRUE, FALSE, UNKNOWN
    reasons: list[str] = field(default_factory=list)
    missing_attributes: list[str] = field(default_factory=list)


def _unknown(attribute: str) -> Evaluation:
    return Evaluation("UNKNOWN", [f"Information required: {attribute}"], [attribute])


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "==": return actual == expected
    if operator == "!=": return actual != expected
    if operator == ">": return actual > expected
    if operator == ">=": return actual >= expected
    if operator == "<": return actual < expected
    if operator == "<=": return actual <= expected
    if operator == "in": return actual in expected
    if operator == "not_in": return actual not in expected
    if operator == "contains": return expected in actual
    if operator == "is_true": return actual is True
    if operator == "is_false": return actual is False
    raise ValueError(f"Unsupported eligibility operator: {operator}")


def evaluate_condition(condition: dict, profile: dict) -> Evaluation:
    if not isinstance(condition, dict):
        raise ValueError("Each condition must be a JSON object")

    if "all" in condition:
        children = [evaluate_condition(c, profile) for c in condition["all"]]
        if any(x.status == "FALSE" for x in children): status = "FALSE"
        elif all(x.status == "TRUE" for x in children): status = "TRUE"
        else: status = "UNKNOWN"
        return _combine(status, children)

    if "any" in condition:
        children = [evaluate_condition(c, profile) for c in condition["any"]]
        if any(x.status == "TRUE" for x in children): status = "TRUE"
        elif all(x.status == "FALSE" for x in children): status = "FALSE"
        else: status = "UNKNOWN"
        return _combine(status, children)

    if "not" in condition:
        child = evaluate_condition(condition["not"], profile)
        status = {"TRUE": "FALSE", "FALSE": "TRUE", "UNKNOWN": "UNKNOWN"}[child.status]
        return Evaluation(status, child.reasons, child.missing_attributes)

    required = {"attribute", "operator", "value"}
    if not required.issubset(condition):
        raise ValueError("Leaf conditions require attribute, operator and value")

    attribute = condition["attribute"]
    if attribute not in profile or profile[attribute] is None or profile[attribute] == "":
        return _unknown(attribute)

    try:
        passed = _compare(profile[attribute], condition["operator"], condition["value"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Could not evaluate '{attribute}': {exc}") from exc

    if passed:
        return Evaluation("TRUE", [f"Condition satisfied: {attribute} {condition['operator']} {condition['value']}"])
    return Evaluation("FALSE", [f"Condition not satisfied: {attribute} {condition['operator']} {condition['value']} (provided: {profile[attribute]})"])


def _combine(status: str, children: list[Evaluation]) -> Evaluation:
    reasons, missing = [], []
    for child in children:
        reasons.extend(child.reasons)
        missing.extend(child.missing_attributes)
    # Missing values matter only when the combined expression is still undecided.
    if status != "UNKNOWN":
        missing = []
    return Evaluation(status, list(dict.fromkeys(reasons)), list(dict.fromkeys(missing)))
