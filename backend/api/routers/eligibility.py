"""
Eligibility API routes. Thin layer: validate -> call service -> return.
All business logic lives in backend/services/eligibility/.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from backend.schemas.eligibility import (
    CriteriaResponse, EligibilityCheckRequest, EligibilityMultiRequest,
    EligibilityResponse, MissingInfoRequest, MissingInfoResponse, MultiResponse,
    SchemeSummary,
)
from backend.services.eligibility.dataset_service import (
    DatasetUnavailableError, SchemeNotFoundError,
)
from backend.services.eligibility.eligibility_service import eligibility_service as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/eligibility", tags=["Eligibility"])


def _not_found(scheme_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found.")


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Eligibility data is not available.")


@router.get("/schemes", response_model=List[SchemeSummary])
def list_schemes():
    """All schemes with their eligibility data status (for dropdowns)."""
    try:
        return svc.list_schemes()
    except DatasetUnavailableError:
        raise _unavailable()


@router.get("/{scheme_id}/criteria", response_model=CriteriaResponse)
def get_criteria(scheme_id: str):
    """Eligibility requirements + the form fields needed for this scheme."""
    try:
        return svc.get_criteria(scheme_id)
    except SchemeNotFoundError:
        raise _not_found(scheme_id)
    except DatasetUnavailableError:
        raise _unavailable()


@router.post("/check", response_model=EligibilityResponse)
def check_eligibility(request: EligibilityCheckRequest):
    """Check one scheme against a temporary user profile (nothing is stored)."""
    try:
        return svc.check(request.scheme_id, request.user_profile.model_dump())
    except SchemeNotFoundError:
        raise _not_found(request.scheme_id)
    except DatasetUnavailableError:
        raise _unavailable()
    except Exception:  # noqa: BLE001 - never leak profile data in errors
        logger.exception("Eligibility check failed for scheme %s", request.scheme_id)
        raise HTTPException(status_code=500, detail="Eligibility check failed.")


@router.post("/check-multiple", response_model=MultiResponse)
def check_multiple(request: EligibilityMultiRequest):
    """Check many schemes at once with the rule engine (no LLM calls)."""
    try:
        return svc.check_multiple(
            request.user_profile.model_dump(), request.scheme_ids,
            request.departments, request.statuses, request.limit)
    except SchemeNotFoundError as exc:
        raise _not_found(str(exc))
    except DatasetUnavailableError:
        raise _unavailable()
    except Exception:  # noqa: BLE001
        logger.exception("Multi-scheme eligibility check failed")
        raise HTTPException(status_code=500, detail="Eligibility check failed.")


@router.post("/missing-information", response_model=MissingInfoResponse)
def missing_information(request: MissingInfoRequest):
    """Which profile fields does this scheme need, and which are still missing?"""
    try:
        return svc.missing_information(request.scheme_id, request.user_profile.model_dump())
    except SchemeNotFoundError:
        raise _not_found(request.scheme_id)
    except DatasetUnavailableError:
        raise _unavailable()
