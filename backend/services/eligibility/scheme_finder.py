"""
Scheme finder: picks WHICH schemes are relevant to the user's topic
("scholarship", "agriculture", "pension"...), before the rule engine decides
who is eligible.

Two signals are combined:
  1. Lexical score over scheme name / department / eligibility / application text
     (always available, deterministic, works offline).
  2. Optional semantic search from the existing RAG retriever
     (passed in as `semantic_fn`; ignored if it fails).
"""

import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

SemanticFn = Callable[[str], List[str]]  # query -> list of scheme_ids (best first)

# keyword groups: asking for any member also searches the whole group
TOPIC_GROUPS = [
    {"scholarship", "scholarships", "stipend", "student", "students", "school",
     "education", "educational", "study", "studies", "hostel", "fee", "fees",
     "chhatravritti", "padhai", "vidyarthi", "coaching", "college", "residential"},
    {"agriculture", "agricultural", "farmer", "farmers", "farming", "kisan", "krishi",
     "crop", "seed", "irrigation", "tractor", "horticulture", "fisheries", "fishery",
     "fisherman", "livestock", "dairy"},
    {"pension", "old age", "senior", "elderly", "widow", "vridha", "vidhwa", "pensioner"},
    {"disability", "disabled", "divyang", "specially abled", "handicapped", "viklang",
     "blind", "deaf"},
    {"women", "woman", "girl", "girls", "female", "mahila", "beti", "ladki", "daughter",
     "maternity", "pregnant", "marriage", "vivah"},
    {"loan", "credit", "subsidy", "business", "self employment", "industry", "startup",
     "entrepreneur", "enterprise", "msme", "skill", "training", "livelihood"},
    {"health", "medical", "insurance", "hospital", "treatment", "medicine"},
    {"travel", "bus", "transport", "pass", "concession", "roadways"},
    {"labour", "labor", "worker", "workers", "construction", "shramik"},
    {"minority", "minorities"},
]


def pretty_department(dept: Optional[str]) -> str:
    text = (dept or "").replace("_", " ").replace("&", "and")
    for wrong, right in (("Justics", "Justice"), ("Coporation", "Corporation")):
        text = text.replace(wrong, right)
    return " ".join(text.split())


def expand_keywords(keywords: Iterable[str], message: str = "") -> List[str]:
    """Expand each keyword with its topic group (and read the message too)."""
    base = {k.strip().lower() for k in keywords if k and k.strip()}
    low = message.lower()
    for group in TOPIC_GROUPS:
        if any(re.search(rf"\b{re.escape(w)}", low) for w in group if len(w) > 3):
            base |= group  # message itself mentions the topic
    expanded = set(base)
    for group in TOPIC_GROUPS:
        if base & group:
            expanded |= group
    return sorted(expanded)


def _count(term: str, text: str) -> int:
    return len(re.findall(rf"\b{re.escape(term)}", text))


def lexical_scores(schemes: List[Dict[str, Any]], terms: List[str]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for s in schemes:
        name = s["scheme_name"].lower()
        dept = pretty_department(s.get("department")).lower()
        elig = (s.get("original_eligibility_text") or "").lower()
        rest = ((s.get("application_process") or "") + " " +
                " ".join(s.get("documents_required", []))).lower()
        score = 0.0
        for term in terms:
            score += 3.0 * min(_count(term, name), 1)
            score += 2.0 * min(_count(term, dept), 1)
            score += 1.0 * min(_count(term, elig), 2)
            score += 0.3 * min(_count(term, rest), 1)
        if score > 0:
            scores[s["scheme_id"]] = score
    return scores


def find_candidates(schemes: List[Dict[str, Any]], keywords: List[str], message: str,
                    semantic_fn: Optional[SemanticFn] = None,
                    limit: int = 60) -> List[Dict[str, Any]]:
    """Return topic-relevant schemes (best first). No topic -> all schemes."""
    terms = expand_keywords(keywords, message)
    if not terms:
        return list(schemes)

    scores = lexical_scores(schemes, terms)
    if semantic_fn:
        try:
            for rank, sid in enumerate(semantic_fn(message)):
                scores[sid] = scores.get(sid, 0.0) + max(0.0, 6.0 - 0.3 * rank)
        except Exception as exc:  # noqa: BLE001 - RAG problems must not break the chat
            logger.warning("Semantic search failed: %s", type(exc).__name__)

    by_id = {s["scheme_id"]: s for s in schemes}
    ranked = sorted((sid for sid in scores if sid in by_id),
                    key=lambda sid: (-scores[sid], by_id[sid]["scheme_name"]))
    result = [by_id[sid] for sid in ranked[:limit]]
    for s in result:
        s["_topic_score"] = round(scores[s["scheme_id"]], 2)
    return result


def find_named_schemes(schemes: List[Dict[str, Any]], message: str) -> List[Dict[str, Any]]:
    """Schemes whose full name appears inside the message."""
    low = re.sub(r"\s+", " ", message.lower())
    hits = [s for s in schemes if len(s["scheme_name"]) > 6
            and re.sub(r"\s+", " ", s["scheme_name"].lower()) in low]
    return sorted(hits, key=lambda s: -len(s["scheme_name"]))[:3]
