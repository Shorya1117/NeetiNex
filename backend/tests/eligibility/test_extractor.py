"""Extractor tests: real sentences from the Jan Soochna data, expected output
checked by hand against the sentence text."""

import pytest

from backend.ingestion.eligibility_structuring.rule_extractor import process_line


def conds(line):
    return [(r["field"], r["operator"], r["value"])
            for r in process_line(line) if r["kind"] == "condition"]


def kinds(line):
    return [r["kind"] for r in process_line(line)]


@pytest.mark.parametrize("line,expected", [
    ("The applicant should be a native of Rajasthan.", [("state", "EQUALS", "Rajasthan")]),
    ("The annual income of the applicants family should be less than Rs.8 lakh per year.",
     [("annual_family_income", "LESS_THAN", 800000)]),
    ("Annual Income sholud be 1.20 Lakhs or less than of it.",
     [("annual_income", "LESS_THAN_OR_EQUAL", 120000)]),
    ("The annual income of the parents from all sources should not exceed Rs.1.00 lakh.",
     [("annual_parent_income", "LESS_THAN_OR_EQUAL", 100000)]),
    ("The applicant should be between 18 to 60 years of age .", [("age", "BETWEEN", [18, 60])]),
    ("The minimum age of the applicant is 18 years or more.", [("age", "GREATER_THAN_OR_EQUAL", 18)]),
    ("Applicant must belong to SBC community.", [("category", "IN", ["SBC"])]),
    ("Applicant should be BPL card holder.", [("bpl_status", "EQUALS", True)]),
    ("The applicant should be suffering from 40 percent disability.",
     [("disability_status", "EQUALS", True), ("disability_percentage", "GREATER_THAN_OR_EQUAL", 40)]),
])
def test_correct_extraction(line, expected):
    assert conds(line) == expected


@pytest.mark.parametrize("line", [
    "The annual income (from all sources) of the families of SC/ST/MBC applicants should not "
    "exceed Rs.2.50 lakh and for O.B. C and EWS category the annual income should not exceed Rs.8 lakh",
    "At the time of applying, the age of the applicant should not be more than 35 years and "
    "only female above 18 years and male above 21 years can apply.",
    "If the student is handicapped, then there should be a certificate of 40% or more disability.",
    "The age of the girl child should be more than 18 years.",
    "The applicant girl student should belong to SBC community or",
    "Girls from (SC/ST/OBC/Minorities/BPL) are eligible.",
    "3 Such journalists and litterateurs who have completed 60 years of age",
])
def test_ambiguous_lines_are_never_auto_structured(line):
    """Risky lines must produce NO mandatory rule - only a manual item."""
    assert conds(line) == [] or "manual" in kinds(line)
    assert "manual" in kinds(line)


def test_leftover_words_flag_manual():
    # 'male only' restriction must not be silently dropped
    out = process_line("Males aged 18 to 60 years.")
    assert "manual" in [r["kind"] for r in out]


def test_original_text_preserved():
    line = "Applicant should be a native resident of Rajasthan."
    assert process_line(line)[0]["source_text"] == line


def test_regression_disability_line_with_transgender_alternative():
    """'Persons with disabilities ... and transgender' lists ALTERNATIVE groups.
    It must not become a mandatory gender rule (caused a false NOT_ELIGIBLE)."""
    line = ("Persons with disabilities of any age who suffer from blindness, low vision, "
            "locomotor disability, leprosy, loss of hearing, mental retardation, any one "
            "or more of the disabilities and transgender.")
    out = process_line(line)
    assert not [r for r in out if r["kind"] == "condition"]
    assert "manual" in [r["kind"] for r in out]


def test_regression_real_dataset_scheme_51_not_gender_restricted():
    import json
    from backend.services.eligibility.dataset_service import DATASET_PATH
    schemes = {s["scheme_id"]: s for s in json.loads(DATASET_PATH.read_text("utf-8"))["schemes"]}
    fields = [r.get("field") for r in schemes["51"]["conditions"]["rules"]]
    assert "gender" not in fields


def test_regression_priority_line_is_not_mandatory():
    line = ("In the distribution of mini-kits, priority is given to Scheduled Castes, "
            "farmers living below the poverty line.")
    assert [r for r in process_line(line) if r["kind"] == "condition"] == []
