"""Pydantic request / response models for the eligibility API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.services.eligibility.field_catalog import (
    CATEGORY_OPTIONS, GENDER_OPTIONS, MARITAL_OPTIONS,
)

# ----------------------------------------------------------------------
# Value normalisation helpers (conservative: unknown values are REJECTED,
# never silently converted)
# ----------------------------------------------------------------------
_GENDER_ALIASES = {
    "male": "male", "m": "male", "man": "male", "boy": "male",
    "female": "female", "f": "female", "woman": "female", "girl": "female",
    "transgender": "transgender", "third gender": "transgender",
}
_CATEGORY_ALIASES = {
    "general": "General", "gen": "General", "unreserved": "General",
    "sc": "SC", "scheduled caste": "SC", "st": "ST", "scheduled tribe": "ST",
    "obc": "OBC", "other backward class": "OBC",
    "mbc": "MBC", "most backward class": "MBC",
    "sbc": "SBC", "special backward class": "SBC",
    "ews": "EWS", "economically weaker section": "EWS",
}
_MARITAL_ALIASES = {
    "unmarried": "unmarried", "single": "unmarried", "never married": "unmarried",
    "married": "married", "widowed": "widowed", "widow": "widowed",
    "widower": "widowed", "divorced": "divorced", "separated": "separated",
}


def _map(value: Optional[str], aliases: Dict[str, str], allowed: List[str], name: str):
    if value is None:
        return None
    key = str(value).strip().lower()
    if key not in aliases:
        raise ValueError(f"{name} must be one of {allowed}")
    return aliases[key]


class UserProfile(BaseModel):
    """
    Temporary user profile. Every field is optional - the engine only asks
    for the fields a particular scheme needs. Nothing here is stored.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    state: Optional[str] = Field(None, max_length=60)
    district: Optional[str] = Field(None, max_length=60)
    category: Optional[str] = None
    annual_family_income: Optional[float] = Field(None, ge=0, le=10**10)
    annual_personal_income: Optional[float] = Field(None, ge=0, le=10**10)
    annual_parent_income: Optional[float] = Field(None, ge=0, le=10**10)
    annual_income: Optional[float] = Field(None, ge=0, le=10**10)
    disability_status: Optional[bool] = None
    disability_percentage: Optional[float] = Field(None, ge=0, le=100)
    bpl_status: Optional[bool] = None
    minority_status: Optional[bool] = None
    occupation: Optional[str] = Field(None, max_length=60)
    marital_status: Optional[str] = None
    is_student: Optional[bool] = None
    current_class: Optional[int] = Field(None, ge=1, le=12)
    highest_class_passed: Optional[int] = Field(None, ge=0, le=12)

    @field_validator("gender")
    @classmethod
    def _gender(cls, v):
        return _map(v, _GENDER_ALIASES, GENDER_OPTIONS, "gender")

    @field_validator("category")
    @classmethod
    def _category(cls, v):
        return _map(v, _CATEGORY_ALIASES, CATEGORY_OPTIONS, "category")

    @field_validator("marital_status")
    @classmethod
    def _marital(cls, v):
        return _map(v, _MARITAL_ALIASES, MARITAL_OPTIONS, "marital_status")

    @field_validator("state", "district", "occupation")
    @classmethod
    def _text(cls, v):
        if v is None:
            return None
        v = " ".join(v.split())
        return v or None


class EligibilityCheckRequest(BaseModel):
    scheme_id: str = Field(..., min_length=1, max_length=40)
    user_profile: UserProfile


class EligibilityMultiRequest(BaseModel):
    user_profile: UserProfile
    scheme_ids: Optional[List[str]] = Field(None, max_length=300)
    departments: Optional[List[str]] = Field(None, max_length=30)
    statuses: Optional[List[str]] = Field(
        None, description="Only return these overall statuses")
    limit: Optional[int] = Field(None, ge=1, le=300)


class MissingInfoRequest(BaseModel):
    scheme_id: str = Field(..., min_length=1, max_length=40)
    user_profile: UserProfile = Field(default_factory=UserProfile)


class SourceReference(BaseModel):
    source_url: Optional[str] = None
    source_document: Optional[str] = None
    verification_status: str = "extracted_unverified"


class ConditionResult(BaseModel):
    rule_id: str
    field: Optional[str] = None
    label: str
    operator: Optional[str] = None
    required_value: Any = None
    provided_value: Any = None
    required_display: str = ""
    provided_display: str = ""
    status: str  # PASS | FAIL | UNKNOWN | NOT_APPLICABLE
    reason_code: Optional[str] = None  # MISSING_INFO | MANUAL_REVIEW | CONFLICT | ...
    mandatory: bool = True
    explanation: str = ""
    source_text: Optional[str] = None
    verification_status: str = "extracted_unverified"


class MissingField(BaseModel):
    field: str
    label: str
    type: str
    why_required: str
    options: Optional[List[str]] = None
    unit: Optional[str] = None
    help: Optional[str] = None


class ManualCheck(BaseModel):
    text: str
    kind: str
    reason: str


class EligibilityResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    overall_status: str  # ELIGIBLE | NOT_ELIGIBLE | NEED_MORE_INFORMATION | UNVERIFIED
    eligible: bool
    matched_conditions: List[ConditionResult] = []
    failed_conditions: List[ConditionResult] = []
    unknown_conditions: List[ConditionResult] = []
    missing_information: List[MissingField] = []
    manual_checks: List[ManualCheck] = []
    explanation: str
    verification_status: str
    source_references: List[SourceReference] = []
    documents_required: List[str] = []
    disclaimer: str = (
        "This result is based on eligibility text collected from the official "
        "portal and structured automatically. Always confirm on the official "
        "source before applying."
    )


class SchemeSummary(BaseModel):
    scheme_id: str
    scheme_name: str
    department: Optional[str] = None
    eligibility_status: str
    auto_checkable_conditions: int
    manual_review_items: int
    required_fields: List[str]


class CriteriaResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    department: Optional[str] = None
    eligibility_status: str
    verification_status: str
    requirements: Dict[str, Any]
    conditions: Dict[str, Any]
    required_fields: List[MissingField]
    manual_checks: List[ManualCheck]
    exclusions: List[str]
    original_eligibility_text: str
    documents_required: List[str]
    source_references: List[SourceReference]


class MultiSchemeResult(BaseModel):
    scheme_id: str
    scheme_name: str
    department: Optional[str] = None
    overall_status: str
    eligible: bool
    matched_conditions: List[ConditionResult] = []
    failed_conditions: List[ConditionResult] = []
    missing_information: List[MissingField] = []
    manual_check_count: int = 0
    verification_status: str
    source_references: List[SourceReference] = []


class MultiResponse(BaseModel):
    total_schemes_evaluated: int
    counts: Dict[str, int]
    results: List[MultiSchemeResult]


class MissingInfoResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    required_fields: List[MissingField]
    missing_fields: List[MissingField]
