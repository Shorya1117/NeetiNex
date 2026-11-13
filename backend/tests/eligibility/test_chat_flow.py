"""Tests for the 'describe yourself -> comparison table' chat flow."""

import json

import pytest

from backend.services.eligibility.chat_eligibility_service import (
    handle_eligibility_chat, run_match,
)
from backend.services.eligibility.dataset_service import DATASET_PATH
from backend.services.eligibility.profile_extractor import (
    extract_profile, looks_like_profile_message, number_in_text,
)
from backend.services.eligibility.scheme_finder import expand_keywords

needs_data = pytest.mark.skipif(not DATASET_PATH.exists(), reason="build the dataset first")


# ---------------- profile extraction ----------------
def test_class_and_parent_income_english():
    r = extract_profile("I am in class 8, my father annual income is 1 lakh, which scholarship?")
    p = r["profile"]
    assert p["current_class"] == 8 and p["is_student"] is True
    assert p["annual_parent_income"] == 100000 and p["highest_class_passed"] == 7
    assert r["intent"] == "find_schemes" and r["assumptions"]  # assumptions are disclosed


def test_hinglish_farmer_district_gives_state():
    p = extract_profile("main kisan hu jaipur me, income 2.5 lakh, agriculture scheme batao")["profile"]
    assert p["occupation"] == "farmer" and p["state"] == "Rajasthan" and p["district"] == "Jaipur"
    assert p["annual_income"] == 250000


def test_hindi_devanagari_digits():
    p = extract_profile("मैं कक्षा १० में हूँ, पिता की आय ५०,००० रुपये है, छात्रवृत्ति बताओ")["profile"]
    assert p["current_class"] == 10 and p["annual_parent_income"] == 50000


def test_passed_class_is_not_current_class():
    p = extract_profile("I have passed 12th, family income 2 lakh, which scheme")["profile"]
    assert p["highest_class_passed"] == 12 and "current_class" not in p


def test_plain_question_is_not_eligibility_intent():
    assert extract_profile("tell me about palanhar yojana")["intent"] == "other"
    assert handle_eligibility_chat("tell me about palanhar yojana") is None


def test_gate_skips_small_talk():
    assert not looks_like_profile_message("hello there")


def test_llm_output_is_validated_and_hallucinations_rejected():
    def fake_llm(prompt):
        return json.dumps({"intent": "find_schemes", "age": 77, "category": "OBC",
                           "income": {"amount_inr": 900000, "basis": "family"},
                           "topic_keywords": ["pension"], "gender": "robot"})
    r = extract_profile("I am OBC, which pension scheme can I get?", fake_llm)
    p = r["profile"]
    assert p["category"] == "OBC"
    assert "age" not in p and "annual_family_income" not in p  # numbers never typed by user
    assert "gender" not in p                                  # invalid value dropped
    assert r["topic_keywords"] == ["pension"]


def test_llm_failure_falls_back_to_regex():
    def broken(prompt):
        raise RuntimeError("boom")
    r = extract_profile("I am in class 9, family income 80000, scholarship?", broken)
    assert r["profile"]["current_class"] == 9 and r["used_llm"] is False


def test_previous_profile_is_merged():
    r = extract_profile("my category is SC", previous={"current_class": 8})
    assert r["profile"]["current_class"] == 8 and r["profile"]["category"] == "SC"


def test_number_guard():
    assert number_in_text(100000, "income 1 lakh") and not number_in_text(900000, "income 1 lakh")


def test_keyword_expansion():
    assert "stipend" in expand_keywords(["scholarship"])
    assert "kisan" in expand_keywords([], "main kisan hu")


# ---------------- table on the real dataset ----------------
@needs_data
def test_class8_student_table():
    out = handle_eligibility_chat(
        "I am in class 8, my father annual income is 1 lakh, which scholarship can I get?")
    assert out["type"] == "eligibility_table" and out["table"]["rows"]
    names = " ".join(r["scheme_name"] for r in out["table"]["rows"])
    assert "Post Matric" not in names          # needs class 10 passed -> excluded
    for row in out["table"]["rows"]:
        assert row["status"] != "NOT_ELIGIBLE"
        for key in ("your_match", "other_conditions", "where_to_apply", "documents"):
            assert key in row
    excluded = " ".join(x["scheme_name"] for x in out["table"]["not_eligible"])
    assert out["table"]["not_eligible_count"] >= 1 and excluded


@needs_data
def test_farmer_table_has_agriculture_schemes():
    out = handle_eligibility_chat(
        "I am a farmer in Jaipur, income 2.5 lakh, tell me agriculture schemes")
    text = " ".join(r["scheme_name"].lower() for r in out["table"]["rows"])
    assert any(w in text for w in ("kisan", "farmer", "fishery", "beej"))


@needs_data
def test_named_scheme_check():
    out = handle_eligibility_chat(
        "I am disabled 50 percent, income 3 lakh, am I eligible for Astha Card Scheme?")
    assert out["table"]["named_scheme"] is True
    assert out["table"]["rows"] == [] and out["table"]["not_eligible_count"] == 1


@needs_data
def test_no_profile_values_means_no_confirmed_eligibility():
    table = run_match({"age": 30}, ["scholarship"], "scholarship")
    assert table["counts"]["ELIGIBLE"] == 0 or all(
        r["your_match"] for r in table["rows"] if r["status"] == "ELIGIBLE")


# ---------------- regressions from real usage ----------------
def test_new_situation_replaces_old_profile():
    """Bug: class-8 details leaked into a later farmer question."""
    old = {"current_class": 8, "is_student": True, "annual_family_income": 100000,
           "highest_class_passed": 7}
    r = extract_profile("main ek kisan hu jaipur me, meri income 2 lakh hai, agriculture schemes", None, old)
    assert r["replaced"] and "current_class" not in r["profile"]
    assert r["profile"]["occupation"] == "farmer"


def test_short_followup_is_merged():
    r = extract_profile("meri category SC hai", None, {"current_class": 8})
    assert not r["replaced"] and r["profile"]["current_class"] == 8


@needs_data
def test_followup_message_returns_table_with_previous_topic():
    prev = {"current_class": 8, "is_student": True, "annual_parent_income": 100000,
            "annual_family_income": 100000, "annual_income": 100000, "highest_class_passed": 7}
    topics = expand_keywords(["scholarship"])
    out = handle_eligibility_chat("meri category SC hai", prev, previous_topics=topics)
    assert out and out["type"] == "eligibility_table"
    assert out["profile"]["category"] == "SC" and out["profile"]["current_class"] == 8


@needs_data
def test_followup_without_previous_topic_is_normal_rag():
    assert handle_eligibility_chat("meri category SC hai", {"current_class": 8}) is None


@needs_data
def test_class8_student_does_not_get_college_schemes():
    out = handle_eligibility_chat(
        "I am in class 8, my father annual income is 1 lakh, which scholarship can I get?")
    names = " ".join(r["scheme_name"] for r in out["table"]["rows"])
    for bad in ("IIT", "College Level", "Women merit", "Urdu Scholarship"):
        assert bad not in names
    reasons = " ".join(x["reason"] for x in out["table"]["not_eligible"])
    assert "education level" in reasons or out["table"]["not_eligible_count"] > 0


@needs_data
def test_farmer_results_are_topic_first():
    out = handle_eligibility_chat(
        "main ek kisan hu jaipur me, meri income 2 lakh hai, agriculture schemes batao")
    top = " ".join(r["scheme_name"].lower() for r in out["table"]["rows"][:5])
    assert any(w in top for w in ("farmer", "kisan", "fishery", "beej", "pond"))
    assert "Class" not in " ".join(out["profile_summary"])


@needs_data
def test_first_answer_returns_topic_for_followups():
    out = handle_eligibility_chat(
        "I am in class 8, my father annual income is 1 lakh, which scholarship can I get?")
    assert "scholarship" in out["topic_keywords"]
    again = handle_eligibility_chat("meri category SC hai", out["profile"],
                                    previous_topics=out["topic_keywords"])
    assert again and again["profile"]["category"] == "SC"


def test_new_intro_with_two_facts_replaces_old_profile():
    from backend.services.eligibility.profile_extractor import extract_profile
    old = {"age": 65, "gender": "female", "marital_status": "widowed", "state": "Rajasthan"}
    r = extract_profile("I am disabled with 50 percent disability, income 1 lakh, "
                        "am I eligible for Astha Card Scheme", None, old)
    assert r["replaced"] and "age" not in r["profile"]
    assert r["profile"]["disability_status"] is True


def test_short_followup_still_merges():
    from backend.services.eligibility.profile_extractor import extract_profile
    r = extract_profile("meri category SC hai", None, {"current_class": 8})
    assert not r["replaced"] and r["profile"]["current_class"] == 8


def test_hindi_student_message_replaces_farmer_profile():
    from backend.services.eligibility.profile_extractor import extract_profile
    old = {"occupation": "farmer", "state": "Rajasthan", "annual_personal_income": 200000}
    r = extract_profile("मैं कक्षा 10 में हूँ, पिता की आय 50,000 रुपये है, छात्रवृत्ति बताओ", None, old)
    assert r["replaced"] and "occupation" not in r["profile"]
