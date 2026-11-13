"""
Reads scheme chunks from the existing Chroma vector store and rebuilds
the per-scheme text (eligibility / documents_required / application_process).

Why Chroma? The project's cleaned JSON files are git-ignored, but every
chunk of them is stored in the Chroma collection used by the RAG system.
So the vector store is the one data source that always ships with the repo.

Two read paths:
  1. chromadb client (normal case, same library the RAG code uses)
  2. direct SQLite read (fallback if chromadb is not installed)
Both are READ-ONLY. The vector store is never modified.
"""

import logging
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

COLLECTION_NAME = "neetinex_schemes"
HEADER = re.compile(r"^Scheme:[^\n]*\nDepartment:[^\n]*\nSection:[^\n]*(?:\n\s*|$)")
MAX_OVERLAP = 160  # chunker used 100 chars of overlap


def _read_with_chromadb(store_dir: Path) -> List[Dict[str, Any]]:
    import chromadb  # local import: optional dependency for this path

    client = chromadb.PersistentClient(path=str(store_dir))
    col = client.get_collection(COLLECTION_NAME)
    data = col.get(include=["documents", "metadatas"])
    return [
        {"text": d, **(m or {})}
        for d, m in zip(data["documents"], data["metadatas"])
    ]


def _read_with_sqlite(store_dir: Path) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(f"file:{store_dir / 'chroma.sqlite3'}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT id, key, COALESCE(string_value, int_value, float_value) "
        "FROM embedding_metadata").fetchall()
    conn.close()
    grouped: Dict[int, Dict[str, Any]] = defaultdict(dict)
    for emb_id, key, value in rows:
        grouped[emb_id][key] = value
    records = []
    for meta in grouped.values():
        meta = dict(meta)
        meta["text"] = meta.pop("chroma:document", "")
        records.append(meta)
    return records


def read_chunks(store_dir: Path) -> List[Dict[str, Any]]:
    """Return every chunk as a flat dict (text + metadata)."""
    try:
        records = _read_with_chromadb(store_dir)
        logger.info("Read %d chunks via chromadb", len(records))
    except ImportError:
        logger.info("chromadb not installed - reading SQLite directly")
        records = _read_with_sqlite(store_dir)
    return records


def _merge_overlap(previous: str, nxt: str) -> str:
    """Join two consecutive chunks, removing the duplicated overlap."""
    nxt = nxt.strip()
    for size in range(min(MAX_OVERLAP, len(previous), len(nxt)), 9, -1):
        if previous.endswith(nxt[:size]):
            return previous + nxt[size:]
    return previous + "\n" + nxt


def rebuild_schemes(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Group chunks by scheme_id and rebuild the section texts.

    Returns {scheme_id: {scheme_name, department, source_url, source_type,
                         source_file, sections: {section_name: text}}}
    """
    by_scheme: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_scheme[str(rec["scheme_id"])].append(rec)

    schemes: Dict[str, Dict[str, Any]] = {}
    for scheme_id, chunks in by_scheme.items():
        chunks.sort(key=lambda c: int(c.get("chunk_index", 0)))
        first = chunks[0]
        sections: Dict[str, str] = {}
        for chunk in chunks:
            body = HEADER.sub("", chunk["text"], count=1).strip()
            name = chunk.get("section", "unknown")
            if not body:
                continue  # header-only chunk
            sections[name] = (
                _merge_overlap(sections[name], body) if name in sections else body
            )
        schemes[scheme_id] = {
            "scheme_id": scheme_id,
            "scheme_name": first.get("scheme_name"),
            "department": first.get("department"),
            "source_url": first.get("source_url"),
            "source_type": first.get("source_type"),
            "source_file": first.get("source_file"),
            "chunk_count": len(chunks),
            "sections": sections,
        }
    return schemes
