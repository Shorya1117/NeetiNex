"""
Bridge between the existing RAG object (NeetiNexRAG) and the eligibility chat.
Keeps backend/api/main.py changes tiny and keeps this package independent of
the RAG internals (everything is passed in as plain functions).
"""

from typing import Callable, List, Optional


def build_llm_fn(rag) -> Optional[Callable[[str], str]]:
    llm = getattr(rag, "llm", None)
    if llm is None:
        return None
    return lambda prompt: llm.invoke(prompt).content


def build_semantic_fn(rag) -> Optional[Callable[[str], List[str]]]:
    retriever = getattr(rag, "retriever", None)
    if retriever is None:
        return None

    def semantic(query: str) -> List[str]:
        docs = retriever.semantic_search(query, n_results=40)
        ids: List[str] = []
        for doc in docs:
            sid = str(doc.metadata.get("scheme_id", ""))
            if sid and sid not in ids:
                ids.append(sid)
        return ids

    return semantic
