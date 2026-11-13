"""Shared fixtures: a small SYNTHETIC dataset so engine tests never depend on
the real crawled data."""

import pytest

from backend.services.eligibility.dataset_service import DatasetService
from backend.services.eligibility.eligibility_service import EligibilityService


def cond(rid, field, op, value, **extra):
    return {"rule_id": rid, "kind": "condition", "field": field, "operator": op,
            "value": value, "mandatory": True, "conflict": False,
            "source_text": f"synthetic {field}", "verification_status": "extracted_unverified",
            **extra}


def manual(rid, text="Some unparsed condition"):
    return {"rule_id": rid, "kind": "manual", "manual_kind": "unparsed",
            "reason": "synthetic", "mandatory": True, "source_text": text}


def scheme(sid, rules, status="fully_structured", verified="extracted_unverified"):
    return {
        "scheme_id": sid, "scheme_name": f"Scheme {sid}", "department": "Test_Dept",
        "eligibility_status": status, "eligibility": {}, "exclusions": [],
        "documents_required": ["Aadhaar Card"], "original_eligibility_text": "text",
        "conditions": {"logic": "AND", "rules": rules},
        "source": {"source_url": "https://example.gov/x", "source_document": "doc",
                   "verification_status": verified},
    }


SYNTHETIC = [
    scheme("S1", [cond("a", "age", "BETWEEN", [18, 60]),
                  cond("b", "annual_family_income", "LESS_THAN_OR_EQUAL", 250000),
                  cond("c", "state", "EQUALS", "Rajasthan"),
                  cond("d", "gender", "EQUALS", "female"),
                  cond("e", "category", "IN", ["SC", "ST"])]),
    scheme("OR1", [{"logic": "OR", "rules": [cond("a", "category", "EQUALS", "SC"),
                                              cond("b", "category", "EQUALS", "ST")]}]),
    scheme("NEST", [cond("a", "age", "GREATER_THAN_OR_EQUAL", 18),
                    {"logic": "OR", "rules": [
                        {"logic": "AND", "rules": [cond("b", "gender", "EQUALS", "female"),
                                                   cond("c", "age", "LESS_THAN", 60)]},
                        cond("d", "disability_status", "EQUALS", True)]}]),
    scheme("NOT1", [{"logic": "NOT", "rules": [cond("a", "bpl_status", "EQUALS", True)]}]),
    scheme("EMPTY", [], status="unstructured"),
    scheme("MANUAL", [cond("a", "age", "GREATER_THAN_OR_EQUAL", 18), manual("m")],
           status="partially_structured"),
    scheme("CONFLICT", [cond("a", "annual_income", "LESS_THAN_OR_EQUAL", 100000, conflict=True),
                        cond("b", "annual_income", "LESS_THAN_OR_EQUAL", 250000, conflict=True)]),
    scheme("OPT", [cond("a", "age", "GREATER_THAN_OR_EQUAL", 18),
                   cond("b", "bpl_status", "EQUALS", True, mandatory=False)]),
    scheme("MAL", [{"rule_id": "x", "kind": "condition", "field": "age",
                    "operator": "RUN_CODE", "value": "__import__('os')"}]),
]

FULL_PROFILE = {"age": 25, "annual_family_income": 180000, "state": "Rajasthan",
                "gender": "female", "category": "SC"}


@pytest.fixture()
def service():
    ds = DatasetService()
    ds._schemes = {s["scheme_id"]: s for s in SYNTHETIC}
    return EligibilityService(ds)
