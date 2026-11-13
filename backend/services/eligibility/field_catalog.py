"""
Field catalog: the single place that describes every user-profile field
the eligibility engine understands.

Used by:
  - the dataset builder (labels for rules)
  - the API (to tell the frontend which form fields to show)
  - the explanation service (human-readable names)

To support a new eligibility field, add it here and (if needed) to the
UserProfile schema. No change is needed in the evaluator.
"""

from typing import Any, Dict, List

GENDER_OPTIONS = ["male", "female", "transgender"]
CATEGORY_OPTIONS = ["General", "SC", "ST", "OBC", "MBC", "SBC", "EWS"]
MARITAL_OPTIONS = ["unmarried", "married", "widowed", "divorced", "separated"]
OCCUPATION_OPTIONS = [
    "farmer", "fisherman", "weaver", "construction_worker",
    "journalist", "artisan", "driver", "student", "other",
]

# type: number | text | select | boolean
FIELD_CATALOG: Dict[str, Dict[str, Any]] = {
    "age": {
        "label": "Age", "type": "number", "unit": "years", "min": 0, "max": 120,
    },
    "gender": {
        "label": "Gender", "type": "select", "options": GENDER_OPTIONS,
    },
    "state": {
        "label": "State of residence (domicile)", "type": "text",
        "help": "State where you are a native / resident, e.g. Rajasthan",
    },
    "category": {
        "label": "Social category", "type": "select", "options": CATEGORY_OPTIONS,
    },
    "annual_family_income": {
        "label": "Annual family income", "type": "number", "unit": "INR", "min": 0,
        "help": "Total yearly income of the whole family (all sources)",
    },
    "annual_personal_income": {
        "label": "Annual personal income (applicant)", "type": "number",
        "unit": "INR", "min": 0,
    },
    "annual_parent_income": {
        "label": "Annual income of parents / guardians", "type": "number",
        "unit": "INR", "min": 0,
    },
    "annual_income": {
        "label": "Annual income", "type": "number", "unit": "INR", "min": 0,
        "help": "This scheme does not say whether personal or family income "
                "is meant - enter the income as per the scheme's income certificate",
    },
    "disability_status": {"label": "Person with disability", "type": "boolean"},
    "disability_percentage": {
        "label": "Disability percentage", "type": "number", "unit": "%",
        "min": 0, "max": 100,
    },
    "bpl_status": {"label": "BPL (Below Poverty Line) family", "type": "boolean"},
    "minority_status": {"label": "Belongs to a notified minority", "type": "boolean"},
    "occupation": {
        "label": "Occupation", "type": "select", "options": OCCUPATION_OPTIONS,
    },
    "marital_status": {
        "label": "Marital status", "type": "select", "options": MARITAL_OPTIONS,
    },
    "is_student": {"label": "Currently a student", "type": "boolean"},
    "highest_class_passed": {
        "label": "Highest class passed", "type": "number", "min": 0, "max": 12,
        "help": "e.g. 10 if you have passed class 10",
    },
    "current_class": {
        "label": "Class currently studying in", "type": "number", "min": 1, "max": 12,
    },
}


def get_field_meta(field: str) -> Dict[str, Any]:
    """Return form metadata for a field (safe default for unknown fields)."""
    meta = FIELD_CATALOG.get(field)
    if meta is None:
        return {"label": field.replace("_", " ").capitalize(), "type": "text"}
    return meta


def field_label(field: str) -> str:
    return get_field_meta(field)["label"]


def describe_fields(fields: List[str]) -> List[Dict[str, Any]]:
    """Form descriptors for a list of fields (order preserved)."""
    return [{"field": f, **get_field_meta(f)} for f in fields]
