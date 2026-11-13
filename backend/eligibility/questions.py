"""Human-readable prompts for attributes reported missing by the rule engine."""
ATTRIBUTE_QUESTIONS = {
    "age": "What is your age in completed years?",
    "annual_family_income": "What is your approximate annual family income in INR?",
    "state": "Which state do you currently reside in?",
    "district": "Which district do you live in?",
    "gender": "What is your gender, if relevant to this scheme?",
    "category": "What is your social category, if relevant to this scheme?",
    "occupation": "What is your occupation?",
    "education_level": "What is your current education level?",
    "is_student": "Are you currently a student?",
    "marital_status": "What is your marital status?",
    "has_disability": "Do you have a disability, if relevant to this scheme?",
    "land_acres": "How much agricultural land does your household own, in acres?",
    "family_size": "How many members are in your family?"
}


def questions_for(attributes):
    return [{"attribute": item, "question": ATTRIBUTE_QUESTIONS.get(item, f"Please provide: {item}")} for item in attributes]
