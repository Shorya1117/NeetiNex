"""
Rule extractor: converts ONE line of scheme eligibility text into
structured rules.

Design principles (accuracy first):
  1. Deterministic regex only - no LLM, same input -> same output.
  2. "Safe" extractors (state, age, income, BPL, disability %, class range)
     may emit a rule even if the rest of the line is not understood.
  3. "Strict" extractors (gender, category, occupation, ...) emit a rule
     only when the WHOLE line is understood (nothing important left over).
  4. Anything not understood is kept as a MANUAL rule with the original
     text. It is never dropped and never treated as "no restriction".
  5. Lines with conditions/exceptions ("if", "except", ...), very long
     lines, or ambiguous numbers become MANUAL, because auto-extraction
     could produce a wrong mandatory rule.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from backend.services.eligibility.field_catalog import field_label

# ----------------------------------------------------------------------
# Operator names (same strings the rule evaluator understands)
# ----------------------------------------------------------------------
EQ, GT, GTE, LT, LTE = (
    "EQUALS", "GREATER_THAN", "GREATER_THAN_OR_EQUAL",
    "LESS_THAN", "LESS_THAN_OR_EQUAL",
)
IN, BETWEEN = "IN", "BETWEEN"

MAX_LINE_LENGTH = 250

# Typos seen in the crawled government text -> corrected ONLY for matching.
# The original text is always stored unchanged.
TYPO_FIXES = {
    "sholud": "should", "shoud": "should", "faimily": "family",
    "famly": "family", "applicants": "applicant", "disable ": "disabled ",
}


@dataclass
class Match:
    field: str
    operator: str
    value: Any
    span: Tuple[int, int]
    strict: bool = False  # strict -> only used if the full line is understood
    extra_spans: Optional[List[Tuple[int, int]]] = None  # other mentions

    def all_spans(self) -> List[Tuple[int, int]]:
        return [self.span] + list(self.extra_spans or [])


# ----------------------------------------------------------------------
# Text helpers
# ----------------------------------------------------------------------

def normalise(line: str) -> str:
    """Lower-case + typo fix + whitespace cleanup (matching copy only)."""
    t = line.lower()
    for wrong, right in TYPO_FIXES.items():
        t = t.replace(wrong, right)
    t = re.sub(r"[–—]", "-", t)
    return re.sub(r"\s+", " ", t).strip()


def strip_numbering(line: str) -> str:
    """Remove list markers like '1.', 'a)', '(ii)' and bullets."""
    line = line.strip().lstrip("-*• ").strip()
    return re.sub(r"^(\(?[a-zA-Z]{1,3}[.)]|\(?\d{1,2}[.)])\s+", "", line)


def is_enumerated_item(line: str) -> bool:
    """'3 Such journalists ...' -> numbered list item (often alternatives)."""
    return bool(re.match(r"^\d{1,2}\s+[A-Z]", line.strip()))


# Only STRUCTURAL words are ignored when checking whether a line was fully
# understood. Words that carry a restriction (not, male, income, age, numbers,
# SC/ST ...) are deliberately NOT here: if such a word is left over after
# extraction, the line is flagged for manual review instead of being trusted.
STOPWORDS = set("""
the of a an should must be is are was were will shall can may has have had been
being applicant candidate beneficiary beneficiaries person persons who whose whom
with by as at on in to for from and or this that these those scheme schemes
under any all only also such their his her its they it eligible eligibility
state resident residents native natives domicile family families belong belongs
belonging category categories community communities caste castes member per
year years annum rajasthan india indian
""".split())

# Extra "glue" words allowed once a rule for that field has been extracted
# (e.g. "age group of ... between" around an age range).
GLUE = {
    "age": set("age aged group between years year old limit upper lower minimum "
               "maximum completed more less than above below over under exceed "
               "exceeding least atleast up upto not older younger greater".split()),
    "income": set("annual income yearly sources source including include total rs "
                  "lakh lakhs lac lacs not exceed exceeding more less than below "
                  "under up upto maximum limit within parents parent guardian "
                  "guardians caretaker caretakers husband student personal "
                  "individual household".split()),
    "bpl": set("bpl card cards holder holders below poverty line".split()),
    "disability": set("disability disabled disabilities handicapped specially abled "
                      "divyang pwd differently suffering percent cent certificate "
                      "certified minimum least atleast more than above person "
                      "persons having".split()),
    "gender": set("girl girls female females women woman ladies lady".split()),
    "occupation": set("registered registration worker workers working card cards certificate".split()),
    "category": set("scheduled tribe tribes other backward most special "
                    "economically weaker section sections class classes".split()),
    "is_student": set("student students studying regular".split()),
    "current_class": set("class classes std grade studying student students".split()),
    "highest_class_passed": set("passed pass cleared completed passing class standard "
                                "exam examination".split()),
}


def glue_for(fields) -> set:
    out = set()
    for f in fields:
        if f.startswith("annual_"):
            out |= GLUE["income"]
        elif f.startswith("disability"):
            out |= GLUE["disability"]
        else:
            out |= GLUE.get(f.replace("_status", ""), GLUE.get(f, set()))
    return out


# letters (2+) or numbers
TOKEN = re.compile(r"[a-z\u0900-\u097f]{2,}|\d+")
STOPWORDS |= {"is", "be", "to", "of", "in", "or", "as", "at", "on", "by", "an",
              "it", "no_", "a"}

# Words that mean the line talks about somebody OTHER than the applicant.
OTHER_SUBJECT = re.compile(
    r"\b(wife|husband|son|sons|daughter|daughters|child|children|parent|parents|"
    r"spouse|dependent|dependents|father|mother|guardian|guardians|orphan)\b"
)

# Words that make a line conditional / exceptional -> too risky to automate.
CONDITIONAL = re.compile(
    r"\b(if|in case|except|unless|however|exempt|exempted|relax|relaxation|"
    r"whereas|provided that|otherwise|but|priority|preference|preferably|"
    r"preferred|given to)\b"
)

DOC_WORDS = re.compile(
    r"aadhaar|aadhar|jan aadhaar|bhamashah|ration card|bank account|passbook|"
    r"photograph|affidavit|certificate|domicile certificate|identity|\bproof\b"
)
BOILERPLATE = re.compile(
    r"\bfalse\b.*\bcancel|cancellation of eligibility|will be responsible|"
    r"above conditions|no age limit|good character|"
    r"all (?:categor(?:y|ies)|nationals)|open to all"
)


def residual_tokens(t: str, spans: List[Tuple[int, int]], extra=frozenset()) -> List[str]:
    """Content words left after removing matched spans and stopwords."""
    chars = list(t)
    for s, e in spans:
        for i in range(s, min(e, len(chars))):
            chars[i] = " "
    left = "".join(chars)
    return [w for w in TOKEN.findall(left)
            if w not in STOPWORDS and w not in extra]


# ----------------------------------------------------------------------
# Individual extractors  (each returns a list of Match)
# ----------------------------------------------------------------------

RE_STATE = re.compile(
    r"\b(?:native|resident|domicile|inhabitant)s?\b[^.;]{0,40}?\brajasthan\b"
    r"(?:\s+state)?"
    r"|\brajasthan\b(?:\s+state)?[^.;]{0,25}?\b(?:native|resident|domicile)\b"
    r"|\bbelongs?\s+to\s+rajasthan(?:\s+state)?"
)


def extract_state(t: str) -> List[Match]:
    m = RE_STATE.search(t)
    if not m or re.search(r"\bnot\b|\bnon\b", m.group(0)):
        return []
    return [Match("state", EQ, "Rajasthan", m.span())]


def _num(x: str) -> Optional[int]:
    try:
        n = int(x)
        return n if 0 < n <= 120 else None
    except ValueError:
        return None


RE_AGE_TRIGGER = re.compile(r"\bage\b|\baged\b|years of age|age group|years old")
RE_AGE_RANGE = re.compile(
    r"(\d{1,3})\s*(?:years?)?\s*(?:to|-|and)\s*(\d{1,3})\s*years?")
RE_AGE_UPPER = re.compile(
    r"(less than|below|under|younger than|not (?:be )?more than|no more than|"
    r"not exceed(?:ing)?|up ?to|maximum(?: age)?(?: limit)?(?: is| of)?)"
    r"\D{0,30}?(\d{1,3})")
RE_AGE_LOWER = re.compile(
    r"(more than|above|over|older than|greater than|at ?least|not less than|"
    r"minimum(?: age)?(?: of| is)?(?: the applicant is)?)\D{0,30}?(\d{1,3})")
RE_AGE_OR_MORE = re.compile(
    r"(\d{1,3})\s*(?:years?)?\s*(?:or more|or above|and above|or older|and older)")
RE_AGE_COMPLETED = re.compile(r"completed\s+(\d{1,3})\s*years? of age")


def extract_age(t: str) -> List[Match]:
    if not RE_AGE_TRIGGER.search(t) or "no age limit" in t:
        return []
    # Subject is not the applicant / limits differ by group -> leave for manual
    if OTHER_SUBJECT.search(t):
        return []
    both_ok = re.search(r"\b(?:male|men)s?\s+(?:and|or)\s+(?:female|women)|"
                        r"\b(?:female|women)s?\s+(?:and|or)\s+(?:male|men)", t)
    if (re.search(r"\b(?:females?|women)\b", t)
            and re.search(r"(?<!fe)\b(?:males?|men)\b", t) and not both_ok):
        return []
    if len(RE_AGE_RANGE.findall(t)) > 1:
        return []
    if re.search(r"\b(limit|age)\b[^.]{0,25}\bfor\b", t):
        return []

    found: List[Match] = []

    def overlaps(span):
        return any(not (span[1] <= m.span[0] or span[0] >= m.span[1]) for m in found)

    m = RE_AGE_RANGE.search(t)
    if m:
        a, b = _num(m.group(1)), _num(m.group(2))
        if a and b and a < b:
            found.append(Match("age", BETWEEN, [a, b], m.span()))
    if found:
        return found

    for m in RE_AGE_COMPLETED.finditer(t):
        n = _num(m.group(1))
        if n:
            found.append(Match("age", GTE, n, m.span()))
    for m in RE_AGE_OR_MORE.finditer(t):
        n = _num(m.group(1))
        if n and not overlaps(m.span()):
            found.append(Match("age", GTE, n, m.span()))
    for m in RE_AGE_UPPER.finditer(t):
        n = _num(m.group(2))
        if not n or overlaps(m.span()):
            continue
        word = m.group(1)
        op = LT if re.match(r"less than|below|under|younger", word) else LTE
        found.append(Match("age", op, n, m.span()))
    for m in RE_AGE_LOWER.finditer(t):
        n = _num(m.group(2))
        if not n or overlaps(m.span()):
            continue
        word = m.group(1)
        op = GTE if re.match(r"at ?least|not less|minimum", word) else GT
        found.append(Match("age", op, n, m.span()))

    # More than 2 age rules, or two rules in the same direction = ambiguous
    dirs = [("max" if m.operator in (LT, LTE) else "min") for m in found]
    if len(found) > 2 or len(set(dirs)) != len(dirs):
        return []
    return found


RE_AMOUNT = re.compile(
    r"(?:rs\.?|₹|inr)\s*([\d,]+(?:\.\d+)?)\s*(?:/-)?\s*(lakhs?|lacs?|crores?)?"
    r"|([\d.]+)\s*(lakhs?|lacs?)")


def _amount_value(m: "re.Match") -> Optional[int]:
    raw = (m.group(1) or m.group(3) or "").replace(",", "").rstrip(".")
    unit = (m.group(2) or m.group(4) or "").lower()
    try:
        val = float(raw)
    except ValueError:
        return None
    if unit.startswith(("lakh", "lac")):
        val *= 100000
    elif unit.startswith("crore"):
        val *= 10000000
    return int(round(val)) if val > 0 else None


def extract_income(t: str) -> List[Match]:
    if "income" not in t or re.search(
            r"tax|vehicle|price|loan|salary|monthly|per month|other means", t):
        return []
    amounts = [(m, _amount_value(m)) for m in RE_AMOUNT.finditer(t)]
    amounts = [(m, v) for m, v in amounts if v]
    if len({v for _, v in amounts}) != 1:
        return []  # none, or several (e.g. different limits per category)
    m, value = amounts[0]
    if re.search(r"or less|not exceed|not (?:be )?more than|up ?to|maximum|within|"
                 r"not above|exceeded", t):
        op = LTE
    elif re.search(r"less than|below|under|lower than", t):
        op = LT
    else:
        return []

    if re.search(r"famil|household", t):
        field = "annual_family_income"
    elif re.search(r"parent|guardian|caretaker|husband", t):
        field = "annual_parent_income"
    elif re.search(r"applicant|student|personal|individual", t):
        field = "annual_personal_income"
    else:
        field = "annual_income"

    key = re.search(r"annual income|yearly income|income", t)
    return [Match(field, op, value, key.span(), extra_spans=[m.span()])]


RE_BPL = re.compile(r"\bbpl\b|below (?:the )?poverty line|poverty line")


def extract_bpl(t: str) -> List[Match]:
    m = RE_BPL.search(t)
    if not m:
        return []
    near = t[max(0, m.start() - 6): m.end() + 6]
    if re.search(r"[/,]|\bor\b|\bnot\b", near):
        return []  # BPL is one of several alternatives, or negated
    return [Match("bpl_status", EQ, True, m.span())]


RE_DISABILITY_PCT = re.compile(
    r"(\d{1,3})\s*(?:%|percent|per cent)(?:\s*or\s*(?:more|above))?")
RE_DISABLED = re.compile(
    r"\b(disabled|disability|disabilities|specially[- ]abled|handicapped|"
    r"divyang|pwd|differently[- ]abled)\b")


def extract_disability(t: str) -> List[Match]:
    out: List[Match] = []
    mp = RE_DISABILITY_PCT.search(t)
    md = RE_DISABLED.search(t)
    if mp and md and not OTHER_SUBJECT.search(t):
        pct = int(mp.group(1))
        if 0 < pct <= 100:
            out.append(Match("disability_status", EQ, True, md.span()))
            out.append(Match("disability_percentage", GTE, pct, mp.span()))
    elif md and not mp:
        mds = list(RE_DISABLED.finditer(t))
        out.append(Match("disability_status", EQ, True, mds[0].span(), strict=True,
                         extra_spans=[m.span() for m in mds[1:]]))
    return out


CATEGORY_PATTERNS = [
    ("SC", r"\bscheduled castes?\b|\bsc\b"),
    ("ST", r"\bscheduled tribes?\b|\bst\b"),
    ("OBC", r"\bother backward class(?:es)?\b|\bobc\b|\bo\.\s?b\.\s?c\b"),
    ("MBC", r"\bmost backward class(?:es)?\b|\bmbc\b"),
    ("SBC", r"\bspecial backward class(?:es)?\b|\bsbc\b"),
    ("EWS", r"\beconomically weaker sections?\b|\bews\b"),
]


def extract_category(t: str) -> List[Match]:
    if re.search(r"minorit|\bbpl\b|\bfemale\b|\bwomen\b", t):
        return []  # mixed lists of alternatives -> manual
    cats, spans = [], []
    for name, pat in CATEGORY_PATTERNS:
        for m in re.finditer(pat, t):
            if name not in cats:
                cats.append(name)
            spans.append(m.span())
    if not cats:
        return []
    m_gen = re.search(r"\bgeneral\b", t)
    if m_gen:
        cats.append("General")
        spans.append(m_gen.span())
    if not spans:
        return []
    return [Match("category", IN, cats, spans[0], strict=True,
                  extra_spans=spans[1:])]


RE_FEMALE = re.compile(r"\b(girls?|females?|women|woman|ladies|lady)\b")


def extract_gender(t: str) -> List[Match]:
    mt = re.search(r"\btransgender\b", t)
    if mt and not RE_FEMALE.search(t):
        return [Match("gender", EQ, "transgender", mt.span(), strict=True)]
    m = RE_FEMALE.search(t)
    if not m or re.search(r"(?<!fe)\bmales?\b|\bman\b|\bmen\b|\bboys?\b", t):
        return []
    return [Match("gender", EQ, "female", m.span(), strict=True)]


OCCUPATIONS = [
    ("farmer", r"\bfarmers?\b|\bkisan\b"),
    ("fisherman", r"\bfisher(?:man|men|folk)\b"),
    ("weaver", r"\bweavers?\b|\bhandloom craftsm[ae]n\b|\bbunkar\b"),
    ("construction_worker", r"\bconstruction workers?\b"),
    ("journalist", r"\bjournalists?\b"),
    ("artisan", r"\bartisans?\b"),
    ("driver", r"\bdrivers?\b"),
]


def extract_occupation(t: str) -> List[Match]:
    hits = []
    for name, pat in OCCUPATIONS:
        m = re.search(pat, t)
        if m:
            hits.append((name, m))
    if len(hits) != 1:
        return []
    name, m = hits[0]
    start = m.start()
    pre = re.search(r"(?:registered\s+(?:as|with)\s+(?:an?\s+)?|working\s+as\s+"
                    r"(?:an?\s+)?)$", t[:start])
    if pre:
        start = pre.start()
    end = m.end()
    post = re.match(r"\s+(?:under\s+(?:the\s+)?(?:labou?r\s+laws?|board))", t[end:])
    if post:
        end += post.end()
    return [Match("occupation", EQ, name, (start, end), strict=True)]


def extract_student(t: str) -> List[Match]:
    m = re.search(r"\bstudents?\b", t)
    if m and not re.search(r"\bnot\b|\bpassed\b|\bpursu|\bcorrespondence\b", t):
        return [Match("is_student", EQ, True, m.span(), strict=True)]
    return []


def extract_marital(t: str) -> List[Match]:
    m = re.search(r"\bwidows?\b", t)
    if m and not re.search(r"\bor\b", t):
        return [Match("marital_status", EQ, "widowed", m.span(), strict=True)]
    m = re.search(r"\bunmarried\b", t)
    if m:
        return [Match("marital_status", EQ, "unmarried", m.span(), strict=True)]
    return []


def extract_minority(t: str) -> List[Match]:
    m = re.search(r"\bminorit(?:y|ies)\b", t)
    if m and not re.search(r"[/,]|\bor\b|\bnot\b", t):
        return [Match("minority_status", EQ, True, m.span(), strict=True)]
    return []


RE_CLASS_RANGE = re.compile(
    r"(?:class(?:es)?|std\.?|grade)\s*(\d{1,2})(?:st|nd|rd|th)?\s*(?:to|-)\s*"
    r"(\d{1,2})(?:st|nd|rd|th)?")


def extract_class_range(t: str) -> List[Match]:
    m = RE_CLASS_RANGE.search(t)
    if not m or "stud" not in t:
        return []
    a, b = int(m.group(1)), int(m.group(2))
    if 1 <= a < b <= 12:
        return [Match("current_class", BETWEEN, [a, b], m.span())]
    return []


RE_PASS_VERB = re.compile(
    r"\b(?:passed|pass|cleared|completed|secured|scored|obtained|qualified|achieved)\b"
    r"[^.;]{0,60}?\b(?:class|std\.?|standard)?\s*(\d{1,2})(?:st|nd|rd|th)\b")
RE_NTH_PASS = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s+(?:class\s+|standard\s+)?pass(?:ed)?\b")


def extract_class_passed(t: str) -> List[Match]:
    """'passed 10th', 'secured 60% in class 12th' -> highest class passed >= N.
    Only when ONE class number is named and no alternatives ('or', '/')."""
    if re.search(r"\bor\b|/", t):
        return []
    hits = [(int(m.group(1)), m.span()) for m in RE_PASS_VERB.finditer(t)]
    hits += [(int(m.group(1)), m.span()) for m in RE_NTH_PASS.finditer(t)]
    numbers = {n for n, _ in hits}
    if len(numbers) != 1:
        return []
    n = numbers.pop()
    if 5 <= n <= 12:
        return [Match("highest_class_passed", GTE, n, hits[0][1])]
    return []


EXTRACTORS = [
    extract_state, extract_age, extract_income, extract_bpl, extract_disability,
    extract_class_range, extract_category, extract_gender, extract_occupation,
    extract_marital, extract_minority, extract_student, extract_class_passed,
]


# ----------------------------------------------------------------------
# Line -> rules
# ----------------------------------------------------------------------

def _condition(match: Match, line: str) -> Dict[str, Any]:
    return {
        "kind": "condition",
        "field": match.field,
        "operator": match.operator,
        "value": match.value,
        "label": field_label(match.field),
        "mandatory": True,
        "conflict": False,
        "source_text": line,
        "confidence": "pattern_match",
        "verification_status": "extracted_unverified",
    }


def _manual(line: str, manual_kind: str, reason: str) -> Dict[str, Any]:
    is_exclusion = bool(re.search(
        r"not eligible|ineligible|will not|should not|shall not|cannot|"
        r"not be allowed|excluded|not entitled", line.lower()))
    return {
        "kind": "manual",
        "manual_kind": "exclusion" if is_exclusion else manual_kind,
        "reason": reason,
        "mandatory": True,
        "source_text": line,
        "verification_status": "needs_manual_review",
    }


def _informational(line: str, reason: str) -> Dict[str, Any]:
    return {
        "kind": "informational",
        "reason": reason,
        "mandatory": False,
        "source_text": line,
    }


def process_line(raw_line: str, enumerated: bool = False) -> List[Dict[str, Any]]:
    """Convert one eligibility line into a list of rule dicts."""
    line = strip_numbering(raw_line)
    if len(line) < 4:
        return []
    t = normalise(line)

    if enumerated:
        return [_manual(line, "enumerated",
                        "Numbered list item - may be one of several alternative "
                        "beneficiary groups")]
    if re.search(r"(?:\bor|\band|,|:|\bof|\bwho)\s*\.?$", t) or t.startswith(("and ", "or ")):
        return [_manual(line, "incomplete",
                        "Sentence looks cut off / part of a list - needs manual reading")]
    if len(line) > MAX_LINE_LENGTH:
        return [_manual(line, "too_long", "Long paragraph - not auto-structured")]
    if CONDITIONAL.search(t):
        return [_manual(line, "conditional",
                        "Contains a condition/exception (if/except/...) - "
                        "needs manual reading")]

    matches: List[Match] = []
    for extractor in EXTRACTORS:
        matches.extend(extractor(t))

    # Other-subject lines (parents, wife, children...) -> strict rules unsafe
    if OTHER_SUBJECT.search(t):
        matches = [m for m in matches if not m.strict]

    # Glue words are allowed only for fields whose rule is actually usable
    def usable(ms):
        return {m.field for m in ms}

    spans = [sp for m in matches for sp in m.all_spans()]
    leftover = residual_tokens(t, spans, glue_for(usable(matches)))
    fully_understood = bool(matches) and not leftover

    rules = [m for m in matches if fully_understood or not m.strict]

    if not rules:
        if BOILERPLATE.search(t) or (DOC_WORDS.search(t) and len(leftover) <= 3):
            return [_informational(line, "Document / procedural statement")]
        return [_manual(line, "unparsed", "No structured rule could be extracted")]

    out = [_condition(m, line) for m in rules]
    if not fully_understood:
        # Part of the line is still unchecked
        if residual_tokens(t, [sp for m in rules for sp in m.all_spans()],
                           glue_for(usable(rules))):
            out.append(_manual(line, "partial",
                               "Part of this line could not be auto-checked"))
    return out
