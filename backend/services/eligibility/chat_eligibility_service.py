"""
Chat eligibility service: the "tell me about yourself -> comparison table" flow.

    user text -> profile (LLM + regex) -> topic schemes (RAG + keywords)
              -> rule engine on each scheme -> table

Returns None when the message is NOT of this kind, so the normal RAG answer
is used. The eligibility DECISION always comes from the rule engine.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from backend.services.eligibility.comparison_service import build_comparison
from backend.services.eligibility.dataset_service import (
    DatasetUnavailableError, dataset_service,
)
from backend.services.eligibility.eligibility_service import eligibility_service
from backend.services.eligibility.explanation_service import indian_rupees
from backend.services.eligibility.profile_extractor import (
    extract_profile, looks_like_profile_message,
)
from backend.services.eligibility.scheme_finder import (
    expand_keywords, find_candidates, find_named_schemes,
)

logger = logging.getLogger(__name__)

PROFILE_LABELS = {
    "age": "Age", "gender": "Gender", "state": "State", "district": "District",
    "category": "Category", "current_class": "Class", "is_student": "Student",
    "annual_family_income": "Family income", "annual_parent_income": "Parents' income",
    "annual_personal_income": "Personal income", "occupation": "Occupation",
    "disability_status": "Disability", "disability_percentage": "Disability %",
    "bpl_status": "BPL", "marital_status": "Marital status",
}
HINDI = {
    "found": "आपकी जानकारी के आधार पर {n} योजनाएँ मिलीं (जाँची गईं: {c})।",
    "none": "आपकी जानकारी के आधार पर कोई उपयुक्त योजना नहीं मिली।",
    "ask": "और सटीक परिणाम के लिए बताइए: {items}।",
    "verify": "कृपया आवेदन से पहले आधिकारिक स्रोत पर शर्तें जाँच लें।",
}
ENGLISH = {
    "found": "Based on your details I found {n} scheme(s) for you (checked {c}).",
    "none": "I could not find any matching scheme for the details you gave.",
    "ask": "To narrow this down, please tell me: {items}.",
    "verify": "Please confirm the conditions on the official source before applying.",
}


def profile_summary(profile: Dict[str, Any]) -> List[str]:
    out = []
    for key, label in PROFILE_LABELS.items():
        if key in profile and profile[key] is not None:
            value = profile[key]
            if isinstance(value, bool):
                value = "Yes" if value else "No"
            elif isinstance(value, (int, float)) and "income" in key:
                value = f"₹{int(value):,}"
            out.append(f"{label}: {value}")
    return out


def _is_hindi(text: str) -> bool:
    return any("ऀ" <= ch <= "ॿ" for ch in text)


def run_match(profile: Dict[str, Any], keywords: List[str], message: str,
              semantic_fn=None, max_rows: int = 12) -> Dict[str, Any]:
    """Profile + topic -> comparison table (no LLM involved)."""
    schemes = dataset_service.all()
    named = find_named_schemes(schemes, message)
    candidates = named or find_candidates(schemes, keywords, message, semantic_fn)
    table = build_comparison(eligibility_service, candidates, profile, max_rows)
    table["named_scheme"] = bool(named)
    return table


def handle_eligibility_chat(message: str, previous_profile: Optional[Dict[str, Any]] = None,
                            llm_fn: Optional[Callable[[str], str]] = None,
                            semantic_fn=None,
                            previous_topics: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    if not looks_like_profile_message(message):
        return None
    extraction = extract_profile(message, llm_fn, previous_profile)

    # Follow-up such as "meri category SC hai": adds new facts to an ongoing
    # search, so keep using the earlier topic and show the updated table.
    follow_up = (bool(previous_profile) and bool(previous_topics)
                 and bool(extraction["new_facts"]) and not extraction["replaced"]
                 and extraction["intent"] != "find_schemes")
    if not follow_up and (extraction["intent"] != "find_schemes" or not extraction["profile"]):
        return None

    keywords = list(extraction["topic_keywords"])
    if follow_up and not keywords:
        keywords = list(previous_topics or [])
    topics = expand_keywords(keywords, message) or list(previous_topics or [])

    try:
        table = run_match(extraction["profile"], keywords, message, semantic_fn)
    except DatasetUnavailableError:
        return None

    text = HINDI if _is_hindi(message) else ENGLISH
    parts = [text["found"].format(n=table["total_matching"], c=table["candidates_checked"])
             if table["rows"] else text["none"]]
    if table["rows"] and table["ask_next"]:
        parts.append(text["ask"].format(items=", ".join(table["ask_next"])))
    parts.append(text["verify"])

    logger.info("eligibility chat: %d rows, %d candidates (profile values not logged)",
                len(table["rows"]), table["candidates_checked"])
    sources = [{"url": r["source_url"]} for r in table["rows"] if r.get("source_url")]
    return {
        "success": True,
        "type": "eligibility_table",
        "answer": " ".join(parts),
        "profile": extraction["profile"],
        "profile_summary": profile_summary(extraction["profile"]),
        "assumptions": extraction["assumptions"],
        "topic_keywords": topics,
        "table": table,
        "sources": sources[:5],
    }
