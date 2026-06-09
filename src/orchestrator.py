from __future__ import annotations

from collections.abc import Callable

from src.load_prompts import load_prompts
from src.router import route
from src.router_llm import route_llm, route_stage2_topic


CONTENT_AGENTS = {
    "clinical_assessment",
    "interpretation",
    "intervention",
    "management",
    "health_services",
    "education",
}

AgentPromptBuilder = Callable[[str, str, str, dict[str, object], dict[str, str]], str]


def orchestrate(
    user_input: str,
    prompts_dir: str = "prompts",
    agent_prompt_builder: AgentPromptBuilder | None = None,
    routing_backend: str = "rules",
) -> dict[str, object]:
    """Build routed agent prompts without running model inference yet."""
    prompts = load_prompts(prompts_dir)
    routing = select_routing_backend(user_input, prompts, prompts_dir, routing_backend)
    routing = apply_stage2_recovery(user_input, routing, prompts_dir)
    prompt_builder = agent_prompt_builder or build_agent_prompt

    executed_agents: list[str] = []
    agent_prompts: dict[str, str] = {}
    if routing["safety_overlay"]:
        executed_agents.append("emergency_overlay")
        agent_prompts["emergency_overlay"] = prompt_builder(
            "emergency_overlay",
            prompts["emergency_overlay"],
            user_input,
            routing,
            prompts,
        )

    primary_agent = str(routing["primary_agent"])
    if primary_agent != "none":
        executed_agents.append(primary_agent)
        agent_prompts[primary_agent] = prompt_builder(
            primary_agent, prompts[primary_agent], user_input, routing, prompts
        )

    secondary_agent = str(routing["secondary_agent"])
    if secondary_agent != "none":
        executed_agents.append(secondary_agent)
        agent_prompts[secondary_agent] = prompt_builder(
            secondary_agent,
            prompts[secondary_agent],
            user_input,
            routing,
            prompts,
        )

    # Real model inference is not connected yet; this is only the prompt bundle
    # that would be sent to the routed modules.
    return {
        "scaffold_prompt_output": compose_scaffold_prompt_output(agent_prompts),
        "routing": routing,
        "executed_agents": executed_agents,
        "agent_prompts": agent_prompts,
    }


def select_routing_backend(
    user_input: str,
    prompts: dict[str, str],
    prompts_dir: str,
    routing_backend: str,
) -> dict[str, object]:
    """Technical router switch only; clinical routing stays inside each router."""
    if routing_backend == "rules":
        routing = route(user_input, prompts)
        return {
            **routing,
            "routing_backend_used": "rules",
            "llm_router_success": False,
            "llm_router_error": "",
            "llm_router_raw_output": {},
        }
    if routing_backend == "llm":
        return route_llm(user_input, prompts_dir)
    raise ValueError('routing_backend must be "rules" or "llm".')


def apply_stage2_recovery(
    user_input: str,
    routing: dict[str, object],
    prompts_dir: str,
) -> dict[str, object]:
    """Use topic-domain recovery only for low-confidence first-stage routing."""
    if routing.get("routing_confidence") != "low":
        return {
            **routing,
            "routing_stage2_used": False,
            "topic_summary": "",
            "stage2_prompt_text": "",
            "stage2_output_text": "",
        }

    stage2 = route_stage2_topic(user_input, prompts_dir)
    topic_summary = stage2["topic_summary"]
    recovered_primary_agent = map_topic_summary_to_primary_agent(topic_summary)
    recovered_routing = {
        **routing,
        "routing_stage2_used": True,
        "topic_summary": topic_summary,
        "stage2_prompt_text": stage2.get("stage2_prompt_text", ""),
        "stage2_output_text": stage2.get("stage2_output_text", ""),
    }

    if recovered_primary_agent is None:
        return recovered_routing

    if recovered_primary_agent == routing.get("primary_agent"):
        return recovered_routing

    return {
        **recovered_routing,
        "primary_agent": recovered_primary_agent,
        "secondary_agent": coherent_secondary_after_stage2(
            str(routing.get("secondary_agent", "none")),
            recovered_primary_agent,
        ),
    }


def map_topic_summary_to_primary_agent(topic_summary: str) -> str | None:
    summary = topic_summary.lower().strip()
    if not summary or summary == "unknown":
        return None

    # Treatment cues come first so "depression medication" and "panic treatment"
    # recover to intervention rather than clinical_assessment.
    if contains_any(
        summary,
        (
            "prescription",
            "medication",
            "medicine",
            "treatment",
            "therapy",
            "drug",
            "intervention",
            "dose",
            "dosage",
            "supplement",
        ),
    ):
        return "intervention"
    if contains_any(
        summary,
        (
            "doctor",
            "provider",
            "clinic",
            "referral",
            "insurance",
            "coverage",
            "paperwork",
            "access",
            "service",
            "care provider",
        ),
    ):
        return "health_services"
    if contains_any(
        summary,
        (
            "prevention",
            "preventive",
            "screening",
            "healthy habit",
            "health promotion",
            "risk reduction",
            "literacy",
            "abbreviation",
            "term meaning",
            "medical term",
            "myth",
        ),
    ):
        return "education"
    if contains_any(
        summary,
        (
            "abnormality",
            "concern",
            "symptom",
            "condition",
            "problem",
            "depression",
            "anxiety",
            "panic",
            "illness",
            "evaluation",
            "serious",
            "worry",
            "abnormal",
            "possible",
        ),
    ):
        return "clinical_assessment"
    return None


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def coherent_secondary_after_stage2(
    secondary_agent: str,
    recovered_primary_agent: str,
) -> str:
    if secondary_agent == "none" or secondary_agent == recovered_primary_agent:
        return "none"
    if secondary_agent in CONTENT_AGENTS:
        return secondary_agent
    return "none"


def build_agent_prompt(
    agent_name: str,
    agent_prompt: str,
    user_input: str,
    routing: dict[str, object],
    prompts: dict[str, str],
) -> str:
    """Build the exact prompt payload; this does not call a model."""
    global_rules = prompts.get("global_rules", "")
    return "\n\n".join(
        part
        for part in (
            f"[{agent_name}]",
            global_rules,
            agent_prompt,
            "USER INPUT:",
            user_input,
            "ROUTING METADATA:",
            str(generation_routing_metadata(routing)),
        )
        if part
    )


def generation_routing_metadata(routing: dict[str, object]) -> dict[str, object]:
    excluded_fields = {
        "stage1_prompt_text",
        "stage1_output_text",
        "stage2_prompt_text",
        "stage2_output_text",
        "llm_router_raw_output",
    }
    return {
        key: value
        for key, value in routing.items()
        if key not in excluded_fields
    }


def compose_scaffold_prompt_output(agent_prompts: dict[str, str]) -> str:
    """Temporary scaffold composition of prompts, not real model output."""
    return "\n\n---\n\n".join(agent_prompts.values()).strip()
