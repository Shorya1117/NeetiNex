"""
Result aggregator: turns evaluated rule results into ONE overall status.

  ELIGIBLE              every mandatory rule PASS (and nothing is left to
                        check manually)
  NOT_ELIGIBLE          at least one mandatory rule FAIL
  NEED_MORE_INFORMATION no mandatory FAIL, but the USER can still supply
                        data that is missing
  UNVERIFIED            no FAIL, nothing missing from the user, but some
                        criteria are manual / conflicting / malformed, so a
                        confirmed decision is not safe
UNKNOWN is never treated as FAIL, and never as PASS.
"""

from typing import Any, Dict, List

from backend.services.eligibility.rule_normalizer import (
    FAIL, MISSING_INFO, NOT_APPLICABLE, PASS, UNKNOWN,
)

ELIGIBLE = "ELIGIBLE"
NOT_ELIGIBLE = "NOT_ELIGIBLE"
NEED_MORE_INFORMATION = "NEED_MORE_INFORMATION"
UNVERIFIED = "UNVERIFIED"


def aggregate_status(top_nodes: List[Dict[str, Any]]) -> str:
    """top_nodes: evaluated children of the scheme's root AND group."""
    relevant = [n for n in top_nodes
                if n.get("mandatory", True) and n["status"] != NOT_APPLICABLE]

    if not relevant:
        return UNVERIFIED  # scheme has no usable criteria at all
    if any(n["status"] == FAIL for n in relevant):
        return NOT_ELIGIBLE
    unknown = [n for n in relevant if n["status"] == UNKNOWN]
    if any(n.get("reason_code") == MISSING_INFO for n in unknown):
        return NEED_MORE_INFORMATION
    if unknown:
        return UNVERIFIED
    if all(n["status"] == PASS for n in relevant):
        return ELIGIBLE
    return UNVERIFIED
