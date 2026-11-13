"""
Test/evaluation report generator.

    python -m backend.tests.eligibility.evaluate_engine

Runs (a) SYNTHETIC scenarios with hand-written expected outcomes and
(b) timing on the REAL dataset. Writes backend/data/eligibility/test_report.json.

IMPORTANT: (a) is synthetic - it proves the engine logic, NOT the accuracy of
the extracted government criteria. Accuracy against real schemes needs
manually verified expected outcomes (see verified_overrides.json workflow).
"""

import json
import time
from pathlib import Path

from backend.services.eligibility.dataset_service import DatasetService
from backend.services.eligibility.eligibility_service import EligibilityService, eligibility_service
from backend.tests.eligibility.conftest import FULL_PROFILE, SYNTHETIC

CASES = [  # (scheme, profile, expected status)
    ("S1", FULL_PROFILE, "ELIGIBLE"),
    ("S1", {**FULL_PROFILE, "age": 17}, "NOT_ELIGIBLE"),
    ("S1", {**FULL_PROFILE, "annual_family_income": 300000}, "NOT_ELIGIBLE"),
    ("S1", {**FULL_PROFILE, "gender": "male"}, "NOT_ELIGIBLE"),
    ("S1", {**FULL_PROFILE, "state": "Punjab"}, "NOT_ELIGIBLE"),
    ("S1", {**FULL_PROFILE, "category": "General"}, "NOT_ELIGIBLE"),
    ("S1", {"age": 30}, "NEED_MORE_INFORMATION"),
    ("S1", {"age": 10}, "NOT_ELIGIBLE"),
    ("OR1", {"category": "ST"}, "ELIGIBLE"),
    ("OR1", {"category": "OBC"}, "NOT_ELIGIBLE"),
    ("NEST", {"age": 30, "gender": "female"}, "ELIGIBLE"),
    ("NEST", {"age": 30, "gender": "male", "disability_status": False}, "NOT_ELIGIBLE"),
    ("NOT1", {"bpl_status": False}, "ELIGIBLE"),
    ("EMPTY", FULL_PROFILE, "UNVERIFIED"),
    ("MANUAL", {"age": 30}, "UNVERIFIED"),
    ("CONFLICT", {"annual_income": 50000}, "UNVERIFIED"),
    ("OPT", {"age": 30, "bpl_status": False}, "ELIGIBLE"),
    ("MAL", {"age": 30}, "UNVERIFIED"),
]


def main() -> None:
    ds = DatasetService()
    ds._schemes = {s["scheme_id"]: s for s in SYNTHETIC}
    svc = EligibilityService(ds)

    passed = false_eligible = false_not_eligible = unknown_wrong = 0
    for sid, profile, expected in CASES:
        got = svc.check(sid, profile)["overall_status"]
        passed += got == expected
        false_eligible += got == "ELIGIBLE" and expected != "ELIGIBLE"
        false_not_eligible += got == "NOT_ELIGIBLE" and expected != "NOT_ELIGIBLE"
        unknown_wrong += expected in ("NEED_MORE_INFORMATION", "UNVERIFIED") and got != expected

    start = time.perf_counter()
    multi = eligibility_service.check_multiple({"age": 30, "state": "Rajasthan"})
    elapsed_ms = (time.perf_counter() - start) * 1000

    report = {
        "synthetic_engine_tests": {
            "total": len(CASES), "passed": passed, "failed": len(CASES) - passed,
            "false_eligible": false_eligible, "false_not_eligible": false_not_eligible,
            "unknown_status_wrong": unknown_wrong,
            "note": "Synthetic hand-written cases - proves engine logic only.",
        },
        "real_dataset_timing": {
            "schemes_evaluated": multi["total_schemes_evaluated"],
            "check_multiple_ms": round(elapsed_ms, 1),
            "status_counts_for_sample_profile": multi["counts"],
        },
        "manually_verified_real_scheme_accuracy": "Not measured yet - needs "
            "reviewer-verified expected outcomes for real schemes.",
    }
    out = Path(__file__).resolve().parents[2] / "data" / "eligibility" / "test_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
