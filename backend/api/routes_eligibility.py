from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from backend.database.eligibility_db import initialize_database
from backend.database.repositories.eligibility_repository import EligibilityRepository
from backend.eligibility.engine import EligibilityEngine
from backend.eligibility.questions import questions_for

router = APIRouter(prefix="/eligibility", tags=["Eligibility"])
initialize_database()
repository = EligibilityRepository()
engine = EligibilityEngine(repository)


class EligibilityCheckRequest(BaseModel):
    scheme_id: str = Field(..., min_length=1)
    profile: dict[str, Any] = Field(default_factory=dict)


class EligibilityMatchRequest(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)


@router.get("/schemes")
def get_eligibility_schemes():
    return {"success": True, "schemes": repository.list_schemes(verified_only=True)}


@router.post("/check")
def check_eligibility(request: EligibilityCheckRequest):
    try:
        result = engine.check_scheme(request.scheme_id, request.profile)
        result["questions"] = questions_for(result["missing_attributes"])
        return {"success": True, "result": result}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/match")
def match_eligible_schemes(request: EligibilityMatchRequest):
    results = engine.match_schemes(request.profile)
    for result in results:
        result["questions"] = questions_for(result["missing_attributes"])
    return {"success": True, "count": len(results), "results": results}
