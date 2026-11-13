"""
Profile extractor: turns a free-text message (English / Hindi / Hinglish)
into a structured user profile for the rule engine.

   "I am in class 8, my father earns 1 lakh a year"
        -> {"is_student": True, "current_class": 8,
            "annual_parent_income": 100000, "annual_family_income": 100000, ...}

How it stays reliable:
  * An LLM (optional) only READS the message and fills a fixed JSON form.
    It never decides eligibility.
  * A deterministic regex extractor runs too. It works with no LLM at all
    and is used to double-check the LLM's numbers (a number the user never
    wrote is rejected).
  * Everything is validated through the same UserProfile model the API uses.
  * Every guess (e.g. "father's income treated as family income") is
    returned in `assumptions` so it can be shown to the user.
"""

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from backend.schemas.eligibility import UserProfile

logger = logging.getLogger(__name__)

LlmFn = Callable[[str], str]

RAJASTHAN_DISTRICTS = {
    "ajmer", "alwar", "banswara", "baran", "barmer", "bharatpur", "bhilwara",
    "bikaner", "bundi", "chittorgarh", "churu", "dausa", "dholpur", "dungarpur",
    "hanumangarh", "jaipur", "jaisalmer", "jalore", "jhalawar", "jhunjhunu",
    "jodhpur", "karauli", "kota", "nagaur", "pali", "pratapgarh", "rajsamand",
    "sawai madhopur", "sikar", "sirohi", "sri ganganagar", "ganganagar", "tonk",
    "udaipur", "beawar", "kotputli", "deeg", "balotra", "phalodi", "salumbar",
}

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९",
                                   "0123456789")

PROFILE_FIELDS = set(UserProfile.model_fields)

# Words that suggest the user is describing themselves / asking for schemes.
GATE = re.compile(
    r"\b(class|std|standard|age|aged|years? old|income|earn|salary|lakh|farmer|"
    r"student|widow|disab|bpl|eligible|eligibility|which scheme|what scheme|"
    r"scholarship|kaun si|konsi|kya mil|mil sakta|mil sakti|labh|laabh|patr|"
    r"i am|i'm|im a|main|mai|mujhe|meri|mera|mere|hum|hamari)\b"
    r"|[ऀ-ॿ]|\d",
    re.I)


# ----------------------------------------------------------------------
# Small parsing helpers
# ----------------------------------------------------------------------

def normalise_text(text: str) -> str:
    return text.translate(_DEVANAGARI_DIGITS)


def _to_rupees(number: str, unit: Optional[str]) -> Optional[float]:
    try:
        value = float(number.replace(",", ""))
    except ValueError:
        return None
    unit = (unit or "").lower()
    if unit in ("lakh", "lakhs", "lac", "lacs", "लाख"):
        value *= 100000
    elif unit in ("crore", "crores", "cr"):
        value *= 10000000
    elif unit in ("thousand", "hazar", "hazaar", "k", "हजार"):
        value *= 1000
    return value


def number_in_text(value: float, text: str) -> bool:
    """Guard against an LLM inventing a number: it must appear in the message."""
    digits = re.sub(r"[,\s]", "", text)
    candidates = {str(int(value))}
    for divisor in (100000, 1000, 10000000):
        if value >= divisor:
            q = value / divisor
            candidates.add(f"{q:g}")
            candidates.add(str(int(q)))
    return any(c and c in digits for c in candidates)


# ----------------------------------------------------------------------
# Deterministic extraction
# ----------------------------------------------------------------------
INCOME_KEYWORDS = r"(?:income|earn\w*|salary|kamai|kamaai|aay|आय|कमाई|तनख्वाह)"
AMOUNT = (r"(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*"
          r"(lakhs?|lacs?|crores?|thousand|hazaar|hazar|k\b|लाख|हजार)?")


def extract_income(text: str) -> Optional[Dict[str, Any]]:
    """Find '<income word> ... <amount>' (either order). Returns amount + basis."""
    for m in re.finditer(INCOME_KEYWORDS, text, re.I):
        window = text[max(0, m.start() - 60): m.end() + 60]
        for a in re.finditer(AMOUNT, window, re.I):
            unit = a.group(2)
            amount = _to_rupees(a.group(1), unit)
            has_currency = bool(re.search(r"rs\.?|₹|inr", a.group(0), re.I))
            if amount and (unit or has_currency or amount >= 1000):
                return {"amount": amount, "basis": _income_basis(window)}
    return None


def _income_basis(window: str) -> str:
    w = window.lower()
    if re.search(r"father|papa|pita|parent|mother|mummy|maa|पिता|पापा|माता|मां|guardian", w):
        return "parents"
    if re.search(r"famil|household|ghar|parivar|परिवार|घर", w):
        return "family"
    if re.search(r"\b(my|mine|self|meri|apni|mera)\b|मेरी|मेरा", w):
        return "self"
    return "unspecified"


def regex_facts(text: str) -> Dict[str, Any]:
    """Facts that can be read with simple, safe patterns."""
    t = normalise_text(text)
    low = t.lower()
    facts: Dict[str, Any] = {}

    m = re.search(r"\b(?:age|aged)\s*(?:is|of|:)?\s*(\d{1,3})\b", low) or re.search(
        r"\b(\d{1,3})\s*(?:years?|yrs?|saal|sal|वर्ष|साल)\b(?!\s*of experience)", low)
    if m and 0 < int(m.group(1)) <= 120:
        facts["age"] = int(m.group(1))

    m = re.search(r"(?:class|std|standard|grade|कक्षा|क्लास)\s*(\d{1,2})", low) or re.search(
        r"\b(\d{1,2})(?:th|st|nd|rd)?\s*(?:class|std|कक्षा|क्लास)", low)
    if m and 1 <= int(m.group(1)) <= 12:
        facts["current_class"] = int(m.group(1))
        facts["is_student"] = True
    elif re.search(r"\b(student|studying|school|college|vidyarthi|padh)\w*|विद्यार्थी|छात्र", low):
        facts["is_student"] = True

    m = re.search(r"(?:passed|pass|cleared|completed)\s+(?:the\s+)?(?:class\s+)?(\d{1,2})(?:th|st|nd|rd)?", low) or \
        re.search(r"\b(\d{1,2})(?:th|st|nd|rd)\s+(?:class\s+)?pass", low)
    if m and 0 < int(m.group(1)) <= 12:
        facts["highest_class_passed"] = int(m.group(1))
        facts.pop("current_class", None)  # "passed 12th" is not "studying in 12th"
        facts.pop("is_student", None)

    income = extract_income(t)
    if income:
        facts["income"] = income

    for name, pat in (("SC", r"\bsc\b|scheduled caste"), ("ST", r"\bst\b|scheduled tribe"),
                      ("OBC", r"\bobc\b|other backward"), ("MBC", r"\bmbc\b"),
                      ("SBC", r"\bsbc\b"), ("EWS", r"\bews\b"),
                      ("General", r"\bgeneral (?:category|caste)|\bgen category")):
        if re.search(pat, low):
            facts["category"] = name
            break

    if re.search(r"\b(girl|female|woman|women|ladki|mahila|beti)\b|लड़की|महिला|बेटी", low):
        facts["gender"] = "female"
    elif re.search(r"\b(boy|male|man|ladka|beta)\b|लड़का|पुरुष", low):
        facts["gender"] = "male"

    if re.search(r"disab|divyang|handicap|viklang|दिव्यांग|विकलांग", low):
        facts["disability_status"] = True
        m = re.search(r"(\d{1,3})\s*(?:%|percent|per cent|प्रतिशत)", low)
        if m and 0 < int(m.group(1)) <= 100:
            facts["disability_percentage"] = int(m.group(1))

    if re.search(r"\bbpl\b|below poverty", low):
        facts["bpl_status"] = True

    for name, pat in (("farmer", r"farmer|kisan|krishak|किसान"),
                      ("weaver", r"weaver|bunkar|handloom"),
                      ("fisherman", r"fisher|machhua|मछुआ"),
                      ("construction_worker", r"construction worker"),
                      ("driver", r"\bdriver\b"), ("journalist", r"journalist"),
                      ("artisan", r"artisan")):
        if re.search(pat, low):
            facts["occupation"] = name
            break

    if re.search(r"\bwidow|vidhwa|विधवा", low):
        facts["marital_status"] = "widowed"
    elif re.search(r"\bunmarried\b", low):
        facts["marital_status"] = "unmarried"

    for district in sorted(RAJASTHAN_DISTRICTS, key=len, reverse=True):
        if re.search(rf"\b{district}\b", low):
            facts["district"] = district.title()
            break
    if re.search(r"rajasthan|राजस्थान", low):
        facts["state"] = "Rajasthan"
    return facts


# ----------------------------------------------------------------------
# LLM extraction (optional)
# ----------------------------------------------------------------------
LLM_PROMPT = """You are a form-filling assistant for an Indian government scheme finder.
Read the user's message (English, Hindi or Hinglish) and fill the JSON below.

RULES
- Use ONLY facts the user explicitly stated. Never guess. Unknown -> null.
- Convert money to rupees as a number (1 lakh = 100000).
- income.basis: "parents" if father/mother/parents' income, "family" if family/household income,
  "self" if the user's own income, otherwise "unspecified".
- intent = "find_schemes" if the user describes themselves/their situation and wants to know which
  schemes/scholarships/benefits they can get or whether they are eligible. Otherwise "other"
  (e.g. asking details of one named scheme with no personal facts, greetings, general questions).
- topic_keywords: 1-4 ENGLISH keywords for the kind of scheme wanted
  (e.g. ["scholarship","education"], ["agriculture","farmer"], ["pension"], ["disability"]).

Return ONLY this JSON, nothing else:
{{"intent": "find_schemes|other", "age": null, "gender": "male|female|transgender|null",
 "state": null, "district": null, "category": "General|SC|ST|OBC|MBC|SBC|EWS|null",
 "income": {{"amount_inr": null, "basis": "unspecified"}},
 "occupation": "farmer|fisherman|weaver|construction_worker|journalist|artisan|driver|student|other|null",
 "marital_status": "unmarried|married|widowed|divorced|separated|null",
 "is_student": null, "current_class": null, "disability_status": null,
 "disability_percentage": null, "bpl_status": null, "minority_status": null,
 "topic_keywords": []}}

USER MESSAGE:
{message}
"""


def llm_facts(message: str, llm_fn: LlmFn) -> Optional[Dict[str, Any]]:
    try:
        raw = llm_fn(LLM_PROMPT.format(message=message))
        match = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(match.group(0)) if match else None
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001 - LLM problems must never break the chat
        logger.warning("LLM profile extraction failed: %s", type(exc).__name__)
        return None


def _clean_llm(data: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Keep only whitelisted, plausible values from the LLM output."""
    text = normalise_text(message)
    out: Dict[str, Any] = {}
    for key in ("gender", "state", "district", "category", "occupation",
                "marital_status", "is_student", "disability_status",
                "bpl_status", "minority_status"):
        value = data.get(key)
        if isinstance(value, str) and value.strip().lower() in ("true", "yes", "haan", "han"):
            value = True
        elif isinstance(value, str) and value.strip().lower() in ("false", "no", "nahi"):
            value = False
        if value not in (None, "", "null"):
            out[key] = value
    for key in ("age", "current_class", "disability_percentage"):
        value = data.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) \
                and number_in_text(value, text):
            out[key] = value
    inc = data.get("income")
    if isinstance(inc, dict) and isinstance(inc.get("amount_inr"), (int, float)) \
            and inc["amount_inr"] > 0 and number_in_text(inc["amount_inr"], text):
        out["income"] = {"amount": float(inc["amount_inr"]),
                         "basis": inc.get("basis") or "unspecified"}
    return out


# ----------------------------------------------------------------------
# Facts -> UserProfile fields
# ----------------------------------------------------------------------

def facts_to_profile(facts: Dict[str, Any], assumptions: List[str]) -> Dict[str, Any]:
    """Map extracted facts to profile fields; record every assumption made."""
    profile = {k: v for k, v in facts.items() if k in PROFILE_FIELDS}

    income = facts.get("income")
    if income:
        amount, basis = income["amount"], income["basis"]
        amount = int(amount) if float(amount).is_integer() else amount
        if basis == "parents":
            profile["annual_parent_income"] = amount
            profile["annual_family_income"] = amount
            profile["annual_income"] = amount
            assumptions.append("Parents' income was also used as the family income "
                               "(schemes use different wording).")
        elif basis == "family":
            profile["annual_family_income"] = amount
            profile["annual_income"] = amount
        elif basis == "self":
            profile["annual_personal_income"] = amount
            profile["annual_income"] = amount
        else:
            profile["annual_family_income"] = amount
            profile["annual_income"] = amount
            profile["annual_personal_income"] = amount
            assumptions.append("You did not say whose income it is - it was used as "
                               "personal, family and general income.")

    if profile.get("district") and not profile.get("state"):
        if str(profile["district"]).lower() in RAJASTHAN_DISTRICTS:
            profile["state"] = "Rajasthan"
            assumptions.append(f"{profile['district']} district -> state taken as Rajasthan.")
    if profile.get("current_class") and profile.get("is_student") is None:
        profile["is_student"] = True
    if profile.get("current_class") and profile.get("highest_class_passed") is None:
        profile["highest_class_passed"] = profile["current_class"] - 1
        assumptions.append(f"Studying in class {profile['current_class']} -> "
                           f"passed up to class {profile['current_class'] - 1}.")
    if profile.get("occupation") == "student":
        profile.pop("occupation")
        profile.setdefault("is_student", True)
    return profile


def validate_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Run through the API's UserProfile model; drop any invalid field."""
    clean: Dict[str, Any] = {}
    for key, value in profile.items():
        if key not in PROFILE_FIELDS or value is None:
            continue
        try:
            checked = UserProfile(**{key: value}).model_dump()[key]
        except ValidationError:
            logger.info("Dropped invalid extracted value for %s", key)
            continue
        if checked is not None:
            clean[key] = checked
    return clean


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------

def looks_like_profile_message(message: str) -> bool:
    """Cheap gate: only messages that may describe a person reach the LLM."""
    return bool(GATE.search(message))


FACT_GROUPS = [
    {"age"}, {"gender"}, {"state", "district"}, {"category"},
    {"annual_family_income", "annual_parent_income", "annual_personal_income", "annual_income"},
    {"occupation"}, {"current_class", "is_student", "highest_class_passed"},
    {"disability_status", "disability_percentage"}, {"bpl_status"}, {"marital_status"},
]
RESET_WORDS = re.compile(r"\b(reset|start over|new person|fresh start|naya|nayi)\b", re.I)


def count_fact_groups(profile: Dict[str, Any]) -> int:
    return sum(1 for group in FACT_GROUPS if group & set(profile))


def extract_profile(message: str, llm_fn: Optional[LlmFn] = None,
                    previous: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Returns {"profile", "new_facts", "assumptions", "topic_keywords",
             "intent", "used_llm"}.
    `previous` = profile from earlier messages of the same chat (merged).
    """
    assumptions: List[str] = []
    facts = regex_facts(message)
    data = llm_facts(message, llm_fn) if llm_fn else None

    topic_keywords: List[str] = []
    intent = None
    if data:
        for key, value in _clean_llm(data, message).items():
            if facts.get(key) is True and value is not True:
                continue  # an explicit keyword match (e.g. "disabled") is not overridden
            facts[key] = value  # LLM understands Hindi/Hinglish better
        topic_keywords = [str(k).lower() for k in data.get("topic_keywords", [])
                          if isinstance(k, str)][:6]
        intent = data.get("intent")

    if facts.get("disability_percentage") and facts.get("disability_status") is None:
        facts["disability_status"] = True
    new_profile = validate_profile(facts_to_profile(facts, assumptions))

    # Does the message ask for schemes? (decided first: it affects replace-vs-merge)
    if intent not in ("find_schemes", "other"):  # no LLM -> simple rule
        asks = re.search(r"scheme|yojana|scholarship|eligible|benefit|labh|laabh|"
                         r"kaun|which|what can|mil sak|योजना|छात्रवृत्ति|पात्र", message, re.I)
        intent = "find_schemes" if (new_profile and asks) else "other"

    # A message that describes a whole new situation REPLACES the earlier details:
    # 3+ kinds of facts, "reset", or an "I am ..." introduction with 2+ facts that
    # asks for schemes. Short follow-ups ("my category is SC") are merged.
    groups = count_fact_groups(new_profile)
    intro = re.search(r"\b(i am|i'm|im a|main|mai|hum)\b|मैं|हम", message, re.I)
    replaced = bool(previous) and (groups >= 3 or bool(RESET_WORDS.search(message))
                                   or (groups >= 2 and bool(intro) and intent == "find_schemes"))
    if replaced:
        merged = dict(new_profile)
        assumptions.insert(0, "Your earlier details were replaced because this message "
                              "describes a new situation.")
    else:
        merged = validate_profile({**(previous or {}), **new_profile})

    return {"profile": merged, "new_facts": new_profile, "replaced": replaced,
            "assumptions": assumptions,
            "topic_keywords": topic_keywords, "intent": intent,
            "used_llm": data is not None}
