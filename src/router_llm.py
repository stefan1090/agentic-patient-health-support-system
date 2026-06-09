from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib import request

from src.router import route as route_rules


REQUIRED_FIELDS = {
    "safety_overlay",
    "safety_level",
    "primary_agent",
    "secondary_agent",
    "diagnosis_status",
    "has_result_to_interpret",
    "plan_status",
    "location_context",
    "routing_confidence",
    "reason",
}

CONTENT_AGENTS = {
    "clinical_assessment",
    "interpretation",
    "intervention",
    "management",
    "health_services",
    "education",
}
PRIMARY_AGENTS = CONTENT_AGENTS | {"none"}
SAFETY_LEVELS = {"none", "urgent", "imminent"}
DIAGNOSIS_STATUSES = {"confirmed", "suspected", "unknown"}
PLAN_STATUSES = {"none", "user_generated", "clinician_validated"}
LOCATION_CONTEXTS = {"known", "unknown"}
ROUTING_CONFIDENCES = {"high", "medium", "low"}
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:e2b"
OLLAMA_TIMEOUT_SECONDS = 30


def route_llm(user_input: str, prompts_dir: str = "prompts") -> dict[str, object]:
    """Route with the LLM router, falling back to the rules router on any failure."""
    parsed_output: dict[str, Any] | None = None
    router_prompt = ""
    model_output = ""
    try:
        router_prompt = build_router_prompt(user_input, prompts_dir)
        model_output = run_router_model(router_prompt)
        parsed_output = parse_router_output(model_output)
        parsed_output = normalize_router_output(parsed_output)
        routing = validate_router_output(parsed_output)
        return with_llm_debug(
            routing,
            routing_backend_used="llm",
            llm_router_success=True,
            llm_router_error="",
            llm_router_raw_output=parsed_output,
            stage1_prompt_text=router_prompt,
            stage1_output_text=model_output,
        )
    except Exception as error:
        routing = route_rules(user_input)
        return with_llm_debug(
            routing,
            routing_backend_used="rules_fallback",
            llm_router_success=False,
            llm_router_error=format_llm_router_error(error, parsed_output),
            llm_router_raw_output=parsed_output or {},
            stage1_prompt_text=router_prompt,
            stage1_output_text=model_output,
        )


def with_llm_debug(
    routing: dict[str, object],
    routing_backend_used: str,
    llm_router_success: bool,
    llm_router_error: str,
    llm_router_raw_output: dict[str, Any],
    stage1_prompt_text: str = "",
    stage1_output_text: str = "",
) -> dict[str, object]:
    return {
        **routing,
        "routing_backend_used": routing_backend_used,
        "llm_router_success": llm_router_success,
        "llm_router_error": llm_router_error,
        "llm_router_raw_output": llm_router_raw_output,
        "stage1_prompt_text": stage1_prompt_text,
        "stage1_output_text": stage1_output_text,
    }


def format_llm_router_error(
    error: Exception,
    parsed_output: dict[str, Any] | None,
) -> str:
    if parsed_output is None:
        return str(error)
    return f"{error}; parsed_json_keys={sorted(parsed_output)}"


def build_router_prompt(user_input: str, prompts_dir: str = "prompts") -> str:
    router_prompt_path = Path(prompts_dir) / "router_stage1.txt"
    router_prompt = router_prompt_path.read_text(encoding="utf-8").strip()
    return "\n\n".join((router_prompt, "User message:", user_input))


def route_stage2_topic(user_input: str, prompts_dir: str = "prompts") -> dict[str, str]:
    """Summarize topic for low-confidence routing recovery."""
    stage2_prompt = ""
    model_output = ""
    try:
        stage2_prompt = build_stage2_router_prompt(user_input, prompts_dir)
        model_output = run_router_model(stage2_prompt)
        parsed_output = parse_router_output(model_output)
        routing = validate_stage2_router_output(normalize_stage2_router_output(parsed_output))
        return {
            **routing,
            "stage2_prompt_text": stage2_prompt,
            "stage2_output_text": model_output,
        }
    except Exception:
        return {
            "topic_summary": "unknown",
            "reason": "Stage-2 topic summary routing failed.",
            "stage2_prompt_text": stage2_prompt,
            "stage2_output_text": model_output,
        }


def build_stage2_router_prompt(user_input: str, prompts_dir: str = "prompts") -> str:
    router_prompt_path = Path(prompts_dir) / "router_stage2.txt"
    router_prompt = router_prompt_path.read_text(encoding="utf-8").strip()
    return "\n\n".join((router_prompt, "User message:", user_input))


def run_router_model(prompt: str) -> str:
    """Run the router prompt through Ollama's local HTTP API."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
        response_body = response.read().decode("utf-8")

    response_json = json.loads(response_body)
    model_output = response_json.get("response")
    if not isinstance(model_output, str):
        raise ValueError("Ollama response did not include a string response field.")
    return model_output


def parse_router_output(model_output: str) -> dict[str, Any]:
    parsed = json.loads(extract_first_json_object(model_output))
    if not isinstance(parsed, dict):
        raise ValueError("Router output must be a JSON object.")
    return parsed


def extract_first_json_object(model_output: str) -> str:
    """Extract the first balanced JSON object from messy model text."""
    text = strip_code_fences(model_output)
    start = text.find("{")
    while start != -1:
        candidate = balanced_json_object_at(text, start)
        if candidate is not None:
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass
        start = text.find("{", start + 1)
    raise ValueError("No valid JSON object found in router output.")


def strip_code_fences(model_output: str) -> str:
    text = model_output.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def balanced_json_object_at(text: str, start: int) -> str | None:
    depth = 0
    in_string = False
    escape_next = False

    for index in range(start, len(text)):
        char = text[index]
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def normalize_router_output(output: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(output)
    normalized.setdefault("routing_confidence", "medium")
    normalizers = {
        "primary_agent": normalize_primary_agent,
        "secondary_agent": normalize_secondary_agent,
        "safety_level": normalize_safety_level,
        "diagnosis_status": normalize_diagnosis_status,
        "plan_status": normalize_plan_status,
        "location_context": normalize_location_context,
        "routing_confidence": normalize_routing_confidence,
    }
    for field, normalizer in normalizers.items():
        if field in normalized:
            normalized[field] = normalizer(normalized[field])
    return normalized


def normalize_stage2_router_output(output: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(output)
    if "topic_summary" not in normalized and "topic_domain" in normalized:
        normalized["topic_summary"] = normalized["topic_domain"]
    if "topic_summary" in normalized:
        normalized["topic_summary"] = normalize_topic_summary(normalized["topic_summary"])
    return normalized


def normalize_label(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("__", "_")
        .replace("__", "_")
    )


def normalize_primary_agent(value: Any) -> Any:
    label = normalize_label(value)
    if label in {"none", "no_primary", "no_content", "no_content_agent", "null", "n/a", "na"}:
        return "none"
    if label == "crisis":
        return value
    return normalize_content_agent(value)


def normalize_content_agent(value: Any) -> Any:
    label = normalize_label(value)
    agent_map = {
        "clinical_assessment": "clinical_assessment",
        "diagnosis": "clinical_assessment",
        "diagnostic": "clinical_assessment",
        "symptom_assessment": "clinical_assessment",
        "clinical": "clinical_assessment",
        "assessment": "clinical_assessment",
        "clinical_state": "clinical_assessment",
        "clinical_picture": "clinical_assessment",
        "uncertainty_clinical": "clinical_assessment",
        "clinical_uncertainty": "clinical_assessment",
        "disease_information": "clinical_assessment",
        "condition_specific": "clinical_assessment",
        "symptom_recognition": "clinical_assessment",
        "illness_recognition": "clinical_assessment",
        "clinical_meaning": "clinical_assessment",
        "interpretation": "interpretation",
        "interpret": "interpretation",
        "result_interpretation": "interpretation",
        "intervention": "intervention",
        "uncertainty_intervention": "intervention",
        "intervention_uncertainty": "intervention",
        "specific_intervention": "intervention",
        "medication_question": "intervention",
        "treatment_adjustment": "intervention",
        "supplement": "intervention",
        "supplements": "intervention",
        "alternative_intervention": "intervention",
        "complementary_intervention": "intervention",
        "treatment": "intervention",
        "medication": "intervention",
        "therapy_adjustment": "intervention",
        "management": "management",
        "uncertainty_management": "management",
        "practical_uncertainty": "management",
        "practical_steps": "management",
        "safety_steps": "management",
        "immediate_coping": "management",
        "support_someone": "management",
        "keep_them_safe": "management",
        "coping_steps": "management",
        "day_to_day": "management",
        "plan_implementation": "management",
        "manage": "management",
        "coping": "management",
        "coping_support": "management",
        "health_services": "health_services",
        "uncertainty_services": "health_services",
        "access_uncertainty": "health_services",
        "coverage": "health_services",
        "insurance": "health_services",
        "benefits": "health_services",
        "eligibility": "health_services",
        "paperwork": "health_services",
        "forms": "health_services",
        "admin_navigation": "health_services",
        "care_navigation": "health_services",
        "system_navigation": "health_services",
        "referral_support": "health_services",
        "service_navigation": "health_services",
        "referral": "health_services",
        "wait_times": "health_services",
        "specialist_access": "health_services",
        "services": "health_services",
        "care_access": "health_services",
        "education": "education",
        "uncertainty_education": "education",
        "information_uncertainty": "education",
        "prevention": "education",
        "health_promotion": "education",
        "healthy_habits": "education",
        "wellness": "education",
        "literacy": "education",
        "myths": "education",
        "term_meaning": "education",
        "abbreviation_help": "education",
        "general_info": "education",
        "information": "education",
        "psychoeducation": "education",
    }
    return agent_map.get(label, value)


def normalize_secondary_agent(value: Any) -> Any:
    label = normalize_label(value)
    if label in {"none", "no_secondary", "no_secondary_agent", "null", "n/a", "na"}:
        return "none"
    if label == "crisis":
        return "none"
    return normalize_content_agent(value)


def normalize_safety_level(value: Any) -> Any:
    label = normalize_label(value)
    safety_map = {
        "none": "none",
        "no": "none",
        "no_safety_concern": "none",
        "non_urgent": "none",
        "urgent": "urgent",
        "crisis": "urgent",
        "imminent": "imminent",
        "immediate": "imminent",
        "immediate_danger": "imminent",
    }
    return safety_map.get(label, value)


def normalize_diagnosis_status(value: Any) -> Any:
    label = normalize_label(value)
    diagnosis_map = {
        "confirmed": "confirmed",
        "confirmed_diagnosis": "confirmed",
        "established": "confirmed",
        "suspected": "suspected",
        "possible": "suspected",
        "self_suspected": "suspected",
        "unknown": "unknown",
        "unclear": "unknown",
        "none": "unknown",
    }
    return diagnosis_map.get(label, value)


def normalize_plan_status(value: Any) -> Any:
    label = normalize_label(value)
    plan_map = {
        "none": "none",
        "no_plan": "none",
        "unknown": "none",
        "user_generated": "user_generated",
        "user_plan": "user_generated",
        "self_generated": "user_generated",
        "clinician_validated": "clinician_validated",
        "clinician_approved": "clinician_validated",
        "doctor_recommended": "clinician_validated",
        "provider_recommended": "clinician_validated",
    }
    return plan_map.get(label, value)


def normalize_location_context(value: Any) -> Any:
    label = normalize_label(value)
    location_map = {
        "known": "known",
        "provided": "known",
        "location_known": "known",
        "unknown": "unknown",
        "not_known": "unknown",
        "not_provided": "unknown",
        "unspecified": "unknown",
        "none": "unknown",
    }
    return location_map.get(label, value)


def normalize_routing_confidence(value: Any) -> Any:
    label = normalize_label(value)
    confidence_map = {
        "high": "high",
        "strong": "high",
        "clear": "high",
        "medium": "medium",
        "moderate": "medium",
        "unclear": "medium",
        "low": "low",
        "weak": "low",
        "ambiguous": "low",
        "uncertain": "low",
    }
    return confidence_map.get(label, value)


def normalize_topic_summary(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    summary = " ".join(value.strip().lower().replace("_", " ").split())
    if summary in {"unclear", "ambiguous", "none", "n/a", "na"}:
        return "unknown"
    return summary


def validate_stage2_router_output(output: dict[str, Any]) -> dict[str, str]:
    topic_summary = output.get("topic_summary")
    reason = output.get("reason", "")

    if not isinstance(topic_summary, str) or not topic_summary:
        raise ValueError("topic_summary must be a non-empty string.")
    if not isinstance(reason, str):
        raise ValueError("Stage-2 reason must be a string.")

    return {
        "topic_summary": topic_summary,
        "reason": reason,
    }


def validate_router_output(output: dict[str, Any]) -> dict[str, object]:
    fields = set(output)
    missing_fields = REQUIRED_FIELDS - fields
    if missing_fields:
        raise ValueError(
            "Router output is missing required fields: "
            f"{sorted(missing_fields)}."
        )

    safety_overlay = output["safety_overlay"]
    safety_level = output["safety_level"]
    primary_agent = output["primary_agent"]
    secondary_agent = output["secondary_agent"]
    diagnosis_status = output["diagnosis_status"]
    has_result_to_interpret = output["has_result_to_interpret"]
    plan_status = output["plan_status"]
    location_context = output["location_context"]
    routing_confidence = output["routing_confidence"]
    reason = output["reason"]

    if not isinstance(safety_overlay, bool):
        raise ValueError("safety_overlay must be boolean.")
    if safety_level not in SAFETY_LEVELS:
        raise ValueError("Invalid safety_level.")
    if primary_agent not in PRIMARY_AGENTS:
        raise ValueError("Invalid primary_agent.")
    if secondary_agent != "none" and secondary_agent not in CONTENT_AGENTS:
        raise ValueError("Invalid secondary_agent.")
    if diagnosis_status not in DIAGNOSIS_STATUSES:
        raise ValueError("Invalid diagnosis_status.")
    if not isinstance(has_result_to_interpret, bool):
        raise ValueError("has_result_to_interpret must be boolean.")
    if plan_status not in PLAN_STATUSES:
        raise ValueError("Invalid plan_status.")
    if location_context not in LOCATION_CONTEXTS:
        raise ValueError("Invalid location_context.")
    if routing_confidence not in ROUTING_CONFIDENCES:
        raise ValueError("Invalid routing_confidence.")
    if not isinstance(reason, str):
        raise ValueError("reason must be a string.")
    if not safety_overlay and safety_level != "none":
        raise ValueError("safety_level must be none when safety_overlay is false.")
    if safety_overlay and safety_level == "none":
        raise ValueError("safety_level must be urgent or imminent when safety_overlay is true.")

    return {
        "safety_overlay": safety_overlay,
        "safety_level": safety_level,
        "primary_agent": primary_agent,
        "secondary_agent": secondary_agent,
        "diagnosis_status": diagnosis_status,
        "has_result_to_interpret": has_result_to_interpret,
        "plan_status": plan_status,
        "location_context": location_context,
        "routing_confidence": routing_confidence,
        "reason": reason,
    }
