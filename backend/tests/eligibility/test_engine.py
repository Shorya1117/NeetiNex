"""Engine tests (synthetic data): the 20 scenarios from the project spec."""

import pytest

from backend.services.eligibility.dataset_service import SchemeNotFoundError
from backend.services.eligibility.rule_engine import evaluate_node
from backend.services.eligibility.result_aggregator import aggregate_status
from backend.tests.eligibility.conftest import FULL_PROFILE


def status(service, sid, profile):
    return service.check(sid, profile)["overall_status"]


# 1-6: all pass / individual failures
def test_all_conditions_satisfied(service):
    r = service.check("S1", FULL_PROFILE)
    assert r["overall_status"] == "ELIGIBLE" and r["eligible"] is True
    assert len(r["matched_conditions"]) == 5 and not r["failed_conditions"]


@pytest.mark.parametrize("field,value", [
    ("age", 17), ("age", 61), ("annual_family_income", 300000),
    ("gender", "male"), ("state", "Punjab"), ("category", "General"),
])
def test_single_mandatory_failure(service, field, value):
    r = service.check("S1", {**FULL_PROFILE, field: value})
    assert r["overall_status"] == "NOT_ELIGIBLE" and r["eligible"] is False
    assert [c["field"] for c in r["failed_conditions"]] == [field]


# 7-9: missing info is UNKNOWN, never FAIL
def test_missing_age(service):
    p = {k: v for k, v in FULL_PROFILE.items() if k != "age"}
    r = service.check("S1", p)
    assert r["overall_status"] == "NEED_MORE_INFORMATION"
    assert [m["field"] for m in r["missing_information"]] == ["age"]
    assert not r["failed_conditions"]


def test_missing_income(service):
    p = {k: v for k, v in FULL_PROFILE.items() if k != "annual_family_income"}
    assert status(service, "S1", p) == "NEED_MORE_INFORMATION"


def test_multiple_missing_fields(service):
    r = service.check("S1", {"age": 30})
    assert r["overall_status"] == "NEED_MORE_INFORMATION"
    assert len(r["missing_information"]) == 4


# 10: fail beats unknown
def test_fail_plus_missing_is_not_eligible(service):
    assert status(service, "S1", {"age": 10}) == "NOT_ELIGIBLE"


# 11-12: OR
def test_or_satisfied(service):
    assert status(service, "OR1", {"category": "ST"}) == "ELIGIBLE"


def test_or_all_alternatives_fail(service):
    assert status(service, "OR1", {"category": "OBC"}) == "NOT_ELIGIBLE"


def test_or_missing(service):
    assert status(service, "OR1", {}) == "NEED_MORE_INFORMATION"


# 13: invalid input is rejected by the profile model
def test_invalid_profile_values():
    from pydantic import ValidationError
    from backend.schemas.eligibility import UserProfile
    for bad in ({"age": -1}, {"age": 200}, {"annual_family_income": -5},
                {"gender": "robot"}, {"category": "XYZ"}, {"unknown_field": 1}):
        with pytest.raises(ValidationError):
            UserProfile(**bad)


def test_profile_normalisation():
    from backend.schemas.eligibility import UserProfile
    p = UserProfile(gender="F", category="scheduled caste", state="  rajasthan ")
    assert (p.gender, p.category, p.state) == ("female", "SC", "rajasthan")


# 14: unknown scheme
def test_unknown_scheme(service):
    with pytest.raises(SchemeNotFoundError):
        service.check("DOES-NOT-EXIST", {})


# 15: no criteria
def test_scheme_without_criteria_is_unverified(service):
    r = service.check("EMPTY", FULL_PROFILE)
    assert r["overall_status"] == "UNVERIFIED" and r["eligible"] is False


# 16, 20: unverified / manual criteria never give ELIGIBLE
def test_manual_condition_blocks_confirmation(service):
    r = service.check("MANUAL", {"age": 30})
    assert r["overall_status"] == "UNVERIFIED" and r["manual_checks"]


def test_manual_but_failed_age_still_not_eligible(service):
    assert status(service, "MANUAL", {"age": 10}) == "NOT_ELIGIBLE"


def test_all_known_pass_but_mandatory_unavailable(service):
    r = service.check("MANUAL", {"age": 99})
    assert r["overall_status"] != "ELIGIBLE"


# 17: conflicting criteria
def test_conflict_never_decided(service):
    r = service.check("CONFLICT", {"annual_income": 50000})
    assert r["overall_status"] == "UNVERIFIED"
    assert all(c["reason_code"] == "CONFLICT" for c in r["unknown_conditions"])


# 18: optional conditions do not decide
def test_optional_condition_ignored(service):
    assert status(service, "OPT", {"age": 30, "bpl_status": False}) == "ELIGIBLE"


# 19: nested AND/OR
@pytest.mark.parametrize("profile,expected", [
    ({"age": 30, "gender": "female"}, "ELIGIBLE"),
    ({"age": 30, "gender": "male", "disability_status": True}, "ELIGIBLE"),
    ({"age": 30, "gender": "male", "disability_status": False}, "NOT_ELIGIBLE"),
    ({"age": 65, "gender": "female", "disability_status": False}, "NOT_ELIGIBLE"),
    ({"age": 30}, "NEED_MORE_INFORMATION"),
])
def test_nested_logic(service, profile, expected):
    assert status(service, "NEST", profile) == expected


def test_not_operator(service):
    assert status(service, "NOT1", {"bpl_status": False}) == "ELIGIBLE"
    assert status(service, "NOT1", {"bpl_status": True}) == "NOT_ELIGIBLE"
    assert status(service, "NOT1", {}) == "NEED_MORE_INFORMATION"


# security: no code execution, malformed rules are contained
def test_malformed_rule_is_unknown_not_executed(service):
    r = service.check("MAL", {"age": 30})
    assert r["overall_status"] == "UNVERIFIED"


def test_depth_limit():
    node = {"rule_id": "x", "kind": "condition", "field": "age",
            "operator": "EQUALS", "value": 1}
    for _ in range(20):
        node = {"logic": "AND", "rules": [node]}
    assert evaluate_node(node, {"age": 1})["status"] == "UNKNOWN"


# determinism
def test_deterministic(service):
    assert service.check("S1", FULL_PROFILE) == service.check("S1", FULL_PROFILE)


def test_aggregate_empty_is_unverified():
    assert aggregate_status([]) == "UNVERIFIED"


# explanations come from the evaluation
def test_income_explanation_text(service):
    r = service.check("S1", {**FULL_PROFILE, "annual_family_income": 350000})
    text = r["failed_conditions"][0]["explanation"]
    assert "exceeds" in text and "₹3,50,000" in text and "₹2,50,000" in text


def test_boundary_values_inclusive(service):
    assert status(service, "S1", {**FULL_PROFILE, "age": 18}) == "ELIGIBLE"
    assert status(service, "S1", {**FULL_PROFILE, "age": 60}) == "ELIGIBLE"
    assert status(service, "S1", {**FULL_PROFILE, "annual_family_income": 250000}) == "ELIGIBLE"
