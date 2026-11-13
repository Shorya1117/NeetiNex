"""
Dataset service: loads the structured eligibility dataset (read-only) and
answers lookups. Only the fixed dataset path below is ever opened.

If the dataset file does not exist yet, it is built automatically ONCE from
the Chroma vector store (the same one-step builder you can run by hand).
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.eligibility.rule_normalizer import is_group

logger = logging.getLogger(__name__)

DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "eligibility" / "eligibility_dataset.json"
)


class SchemeNotFoundError(Exception):
    """Unknown scheme id."""


class DatasetUnavailableError(Exception):
    """Dataset missing or unreadable."""


class DatasetService:
    def __init__(self, path: Path = DATASET_PATH):
        self._path = path
        self._lock = threading.Lock()
        self._schemes: Optional[Dict[str, Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    def _load(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            if self._schemes is not None:
                return self._schemes
            if not self._path.exists():
                self._auto_build()
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._schemes = {str(s["scheme_id"]): s for s in data["schemes"]}
            except (OSError, ValueError, KeyError) as exc:
                logger.error("Cannot read eligibility dataset: %s", exc)
                raise DatasetUnavailableError("Eligibility dataset is unavailable") from exc
            logger.info("Loaded %d eligibility records", len(self._schemes))
            return self._schemes

    def _auto_build(self) -> None:
        logger.info("Eligibility dataset missing - building from vector store")
        try:
            from backend.ingestion.eligibility_structuring.build_eligibility_dataset import (
                build_dataset,
            )
            build_dataset(output_dir=self._path.parent)
        except Exception as exc:  # noqa: BLE001 - surface as one clean error
            logger.error("Automatic dataset build failed: %s", exc)
            raise DatasetUnavailableError("Eligibility dataset is unavailable") from exc

    def reload(self) -> None:
        with self._lock:
            self._schemes = None

    # ------------------------------------------------------------------
    def get(self, scheme_id: str) -> Dict[str, Any]:
        scheme = self._load().get(str(scheme_id).strip())
        if scheme is None:
            raise SchemeNotFoundError(scheme_id)
        return scheme

    def all(self) -> List[Dict[str, Any]]:
        return list(self._load().values())


def iter_leaf_rules(node: Dict[str, Any]):
    """Yield every leaf rule inside a (possibly nested) condition group."""
    if is_group(node):
        for child in node.get("rules", []):
            yield from iter_leaf_rules(child)
    else:
        yield node


def required_fields(scheme: Dict[str, Any]) -> Dict[str, str]:
    """
    Profile fields needed to evaluate this scheme, in rule order.
    Returns {field: why_required (original source sentence)}.
    """
    fields: Dict[str, str] = {}
    for rule in iter_leaf_rules(scheme["conditions"]):
        if rule.get("kind", "condition") != "condition" or rule.get("conflict"):
            continue
        field = rule.get("field")
        if field and field not in fields:
            fields[field] = rule.get("source_text") or ""
    return fields


dataset_service = DatasetService()
