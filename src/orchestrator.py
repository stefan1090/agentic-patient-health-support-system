from __future__ import annotations

from collections.abc import Callable

from src.load_prompts import load_prompts
from src.router import route
from src.router_llm import route_llm


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
            str(routing),
        )
        if part
    )


def compose_scaffold_prompt_output(agent_prompts: dict[str, str]) -> str:
    """Temporary scaffold composition of prompts, not real model output."""
    return "\n\n---\n\n".join(agent_prompts.values()).strip()
