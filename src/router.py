from __future__ import annotations


CONTENT_AGENTS = {
    "clinical_assessment",
    "interpretation",
    "intervention",
    "management",
    "health_services",
    "education",
}


def route(user_input: str, prompts: dict[str, str] | None = None) -> dict[str, object]:
    """Return routing metadata in the schema defined by prompts/router.txt."""
    text = user_input.lower()

    safety_level = _safety_level(text)
    diagnosis_status = _diagnosis_status(text)
    has_result_to_interpret = _has_result_to_interpret(text)
    plan_status = _plan_status(text)
    location_context = _location_context(text)
    local_need = _local_need(text)

    primary_agent = _primary_agent(
        text=text,
        safety_level=safety_level,
        diagnosis_status=diagnosis_status,
        has_result_to_interpret=has_result_to_interpret,
        local_need=local_need,
    )
    secondary_agent = _secondary_agent(
        text=text,
        primary_agent=primary_agent,
        has_result_to_interpret=has_result_to_interpret,
        local_need=local_need,
    )

    return {
        "safety_overlay": safety_level != "none",
        "safety_level": safety_level,
        "primary_agent": primary_agent,
        "secondary_agent": secondary_agent,
        "diagnosis_status": diagnosis_status,
        "has_result_to_interpret": has_result_to_interpret,
        "plan_status": plan_status,
        "location_context": location_context,
        "reason": _reason(safety_level, primary_agent, secondary_agent),
    }


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _safety_level(text: str) -> str:
    imminent_terms = (
        "i am going to kill myself",
        "i'm going to kill myself",
        "i will kill myself",
        "kill myself now",
        "end my life now",
        "can't stay safe",
        "cannot stay safe",
        "going to hurt myself",
        "going to hurt someone",
        "going to harm someone",
        "immediate danger",
        "imminent danger",
    )
    urgent_terms = (
        "suicide",
        "suicidal",
        "self-harm",
        "self harm",
        "i don't want to be here",
        "i dont want to be here",
        "i want to disappear",
        "i can't do this anymore",
        "i cant do this anymore",
        "i might hurt myself",
        "life is not worth it",
        "hurt myself",
        "harm myself",
        "hurt themselves",
        "hurt others",
        "harm others",
        "psychosis",
        "abuse",
    )
    if _contains_any(text, imminent_terms):
        return "imminent"
    if _contains_any(text, urgent_terms):
        return "urgent"
    return "none"


def _diagnosis_status(text: str) -> str:
    confirmed_terms = (
        "i was diagnosed with",
        "i have been diagnosed with",
        "my doctor told me i have",
        "my clinician told me i have",
        "confirmed diagnosis",
        "i am on medication for",
        "i'm on medication for",
        "i take medication for",
        "i have been treated for",
        "i was treated for",
    )
    direct_condition_terms = (
        "i have depression",
        "i have anxiety",
        "i have adhd",
        "i have bipolar",
        "i have ptsd",
        "i have ocd",
    )
    suspected_terms = (
        "i think i have",
        "i feel like i have",
        "i probably have",
        "do i have",
        "could i have",
        "might have",
        "suspect i have",
    )
    if _contains_any(text, confirmed_terms):
        return "confirmed"
    if _has_treatment_context_for_condition(text):
        return "confirmed"
    if _contains_any(text, suspected_terms):
        return "suspected"
    if _contains_any(text, direct_condition_terms):
        return "confirmed"
    return "unknown"


def _has_treatment_context_for_condition(text: str) -> bool:
    treatment_starts = (
        "i am on ",
        "i'm on ",
        "i take ",
    )
    condition_terms = (
        " for depression",
        " for anxiety",
        " for adhd",
        " for bipolar",
        " for ptsd",
        " for ocd",
    )
    return _contains_any(text, treatment_starts) and _contains_any(text, condition_terms)


def _has_result_to_interpret(text: str) -> bool:
    result_terms = (
        "lab result",
        "lab results",
        "test result",
        "test results",
        "blood test",
        "bloodwork",
        "diagnostic test report",
        "test report",
        "imaging",
        "mri",
        "ct scan",
        "x-ray",
        "xray",
        "screening score",
        "phq-9",
        "phq9",
        "gad-7",
        "gad7",
        "questionnaire",
    )
    return _contains_any(text, result_terms)


def _plan_status(text: str) -> str:
    clinician_terms = (
        "my doctor told me to",
        "my clinician told me to",
        "my therapist told me to",
        "clinician validated",
        "doctor gave me a plan",
        "treatment plan",
    )
    user_terms = (
        "my plan is",
        "i made a plan",
        "i want to try",
        "i am planning to",
        "i'm planning to",
    )
    if _contains_any(text, clinician_terms):
        return "clinician_validated"
    if _contains_any(text, user_terms):
        return "user_generated"
    return "none"


def _location_context(text: str) -> str:
    location_terms = (
        "united states",
        "usa",
        "u.s.",
        "uk",
        "united kingdom",
        "canada",
        "australia",
        "india",
        "germany",
        "france",
        "state",
        "province",
        "county",
        "city",
        "nhs",
        "medicaid",
        "medicare",
        "where i live",
    )
    place_patterns = (
        "in boston",
        "in california",
        "in nyc",
        "in new york",
        "in london",
        "in toronto",
    )
    return (
        "known"
        if _contains_any(text, location_terms) or _contains_any(text, place_patterns)
        else "unknown"
    )


def _local_need(text: str) -> bool:
    local_terms = (
        "near me",
        "nearby",
        "around me",
        "local",
        "in my area",
        "where can i go",
        "where to go",
    )
    return _contains_any(text, local_terms)


def _primary_agent(
    text: str,
    safety_level: str,
    diagnosis_status: str,
    has_result_to_interpret: bool,
    local_need: bool,
) -> str:
    if safety_level != "none" and not _has_non_crisis_content_intent(
        text,
        diagnosis_status,
        has_result_to_interpret,
        local_need,
    ):
        return "none"
    if _asks_about_clinical_assessment(text, diagnosis_status):
        return "clinical_assessment"
    if has_result_to_interpret:
        return "interpretation"
    if _asks_about_services(text, local_need):
        return "health_services"
    if _asks_about_management_intent(text):
        return "management"
    if _asks_about_specific_intervention(text):
        return "intervention"
    return "education"


def _secondary_agent(
    text: str,
    primary_agent: str,
    has_result_to_interpret: bool,
    local_need: bool,
) -> str:
    candidates: list[str] = []
    if has_result_to_interpret:
        candidates.append("interpretation")
    if _asks_about_services(text, local_need):
        candidates.append("health_services")
    if _asks_about_management_intent(text):
        candidates.append("management")
    if _asks_about_specific_intervention(text) and not _asks_about_management_intent(text):
        candidates.append("intervention")

    for candidate in candidates:
        if candidate != primary_agent:
            return candidate
    return "none"


def _has_non_crisis_content_intent(
    text: str,
    diagnosis_status: str,
    has_result_to_interpret: bool,
    local_need: bool,
) -> bool:
    return (
        _asks_about_clinical_assessment(text, diagnosis_status)
        or has_result_to_interpret
        or _asks_about_services(text, local_need)
        or _asks_about_management_intent(text)
        or _asks_about_specific_intervention(text)
        or _asks_about_education(text)
    )


def _asks_about_clinical_assessment(text: str, diagnosis_status: str) -> bool:
    if _has_uncertainty_language(text):
        return _asks_about_clinical_uncertainty(text, diagnosis_status)
    if _asks_about_condition_clinical_meaning(text):
        return True
    clinical_terms = (
        "symptom",
        "symptoms",
        "signs",
        "mental illness",
        "diagnosis",
        "diagnosed",
        "do i have",
        "could i have",
        "might have",
        "what condition",
        "what could this mean",
        "what does this suggest",
        "clinical picture",
        "clinical state",
        "getting worse",
        "worsening",
        "progression",
        "progressing",
        "relapse",
        "relapsing",
        "flare",
        "change in my condition",
        "specific condition",
        "specific disease",
    )
    return diagnosis_status == "suspected" or _contains_any(text, clinical_terms)


def _asks_about_condition_clinical_meaning(text: str) -> bool:
    non_clinical_terms = (
        "abbreviation",
        "term",
        "meaning",
        "myth",
        "prevention",
        "health promotion",
        "healthy habit",
        "wellness",
        "insurance",
        "coverage",
        "benefits",
        "eligibility",
        "paperwork",
        "form",
        "service",
        "referral",
        "facility",
        "medication",
        "medicine",
        "dose",
        "therapy",
        "supplement",
        "herb",
        "biomagnetism",
        "acupuncture",
        "digital tool",
        "bid",
    )
    if text.startswith("what is ") and not _contains_any(text, non_clinical_terms):
        return True

    clinical_patterns = (
        "what does ",
        "how do you recognize ",
        "how do i recognize ",
        "what are the signs of ",
        "what are signs of ",
        "what are the symptoms of ",
        "what are symptoms of ",
        "how does ",
        "what does worsening ",
        "what does it mean if ",
    )
    clinical_objects = (
        "condition",
        "disease",
        "illness",
        "syndrome",
        "disorder",
        "infection",
        "injury",
        "symptoms",
        "signs",
        "progress",
        "progression",
        "worsening",
        "relapse",
        "flare",
        "look like",
        "recognize",
    )
    return _contains_any(text, clinical_patterns) and _contains_any(
        text, clinical_objects
    )


def _has_uncertainty_language(text: str) -> bool:
    uncertainty_terms = (
        "i'm not sure",
        "im not sure",
        "i am not sure",
        "i don't know",
        "i dont know",
        "i don't understand",
        "i dont understand",
        "i want to understand better",
        "i need more clarity",
    )
    return _contains_any(text, uncertainty_terms)


def _asks_about_clinical_uncertainty(text: str, diagnosis_status: str) -> bool:
    clinical_uncertainty_terms = (
        "condition",
        "diagnosis",
        "disease",
        "illness",
        "syndrome",
        "disorder",
        "infection",
        "injury",
        "have ",
        "clinical picture",
        "clinical state",
        "symptoms indicate",
        "sounds like relapse",
        "relapse",
        "worsening",
        "progression",
        "flare",
    )
    return diagnosis_status == "suspected" or _contains_any(
        text, clinical_uncertainty_terms
    )


def _asks_about_specific_intervention(text: str) -> bool:
    intervention_terms = (
        "venlafaxine",
        "citalopram",
        "sertraline",
        "fluoxetine",
        "prozac",
        "lexapro",
        "escitalopram",
        "melatonin",
        "supplement",
        "supplements",
        "herb",
        "herbs",
        "biomagnetism",
        "acupuncture",
        "medication",
        "medicine",
        "dose",
        "dosage",
        "increase",
        "decrease",
        "adjust",
        "adjusting",
        "start",
        "starting",
        "add",
        "adding",
        "switching",
        "stopping",
        "stop my",
        "stop taking",
        "therapy adjustment",
        "cbt",
        "dbt",
        "therapy",
        "psychotherapy",
        "treatment",
    )
    focus_terms = (
        "should i",
        "should",
        "can i",
        "does",
        "do they",
        "will",
        "why",
        "how does",
        "how do",
        "is it safe",
        "help",
        "work",
        "use",
        "take",
        "try",
        "planning to",
    )
    return _contains_any(text, intervention_terms) and _contains_any(text, focus_terms)


def _asks_about_management_intent(text: str) -> bool:
    management_terms = (
        "manage",
        "cope",
        "coping",
        "coping steps",
        "day to day",
        "day-to-day",
        "practical actions",
        "what to do right now",
        "what should i do",
        "what do i do now",
        "do right now",
        "handle this",
        "night by night",
        "get through tonight",
        "how do i get through tonight",
        "how do i stay safe",
        "how do i keep them safe",
        "how do i help them",
        "how do i support them right now",
        "follow a plan",
        "follow this plan",
        "carry out",
        "prevent worsening",
        "until i can see a doctor",
        "what to do tonight",
        "get through this safely",
        "practical steps",
        "immediate steps",
    )
    return _contains_any(text, management_terms)


def _asks_about_services(text: str, local_need: bool = False) -> bool:
    service_terms = (
        "where to go",
        "where can i go",
        "where should i go",
        "service",
        "services",
        "what service should i use",
        "what kind of facility",
        "what level of care",
        "access care",
        "get care",
        "referral",
        "specialist",
        "psychiatrist",
        "wait time",
        "wait times",
        "care pathway",
        "care pathways",
        "insurance",
        "coverage",
        "covered",
        "benefits",
        "eligibility",
        "paperwork",
        "forms",
        "authorization",
        "prior authorization",
        "navigate the system",
        "navigation",
        "verify coverage",
        "verify benefits",
        "faster",
        "clinic",
        "no mental health clinic",
    )
    local_service_terms = (
        "care",
        "clinic",
        "clinician",
        "doctor",
        "therapist",
        "psychiatrist",
        "psychologist",
    )
    return _contains_any(text, service_terms) or (
        local_need and _contains_any(text, local_service_terms)
    )


def _asks_about_education(text: str) -> bool:
    education_terms = (
        "prevention",
        "prevention of",
        "health promotion",
        "healthy habits",
        "wellness habits",
        "myth",
        "myths",
        "abbreviation",
        "meaning of term",
        "what does",
        "mean",
        "meaning",
        "term",
        "bid",
        "general literacy",
        "general information",
    )
    return _contains_any(text, education_terms)


def _reason(safety_level: str, primary_agent: str, secondary_agent: str) -> str:
    parts = [f"Primary route is {primary_agent}."]
    if secondary_agent != "none":
        parts.append(f"Secondary route is {secondary_agent}.")
    if safety_level != "none":
        parts.append(f"Safety overlay is {safety_level}.")
    return " ".join(parts)
