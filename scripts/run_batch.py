from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.export import write_csv
from src.orchestrator import orchestrate


INPUT_PATH = Path("data/test_10.csv")
OUTPUT_PATH = Path("data/outputs/test_10_outputs.csv")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--routing-backend",
        choices=("rules", "llm"),
        default="rules",
    )
    args = parser.parse_args()

    rows = []
    with INPUT_PATH.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            user_input = row.get("case", "")
            result = orchestrate(user_input, routing_backend=args.routing_backend)
            routing = result["routing"]
            rows.append(
                {
                    **row,
                    # Real model inference is not connected yet; this column is
                    # a scaffold prompt bundle, not a final clinical answer.
                    "scaffold_prompt_output": result["scaffold_prompt_output"],
                    "executed_agents": json.dumps(result.get("executed_agents", [])),
                    "agent_prompts": json.dumps(result.get("agent_prompts", {})),
                    "safety_overlay": routing["safety_overlay"],
                    "safety_level": routing["safety_level"],
                    "primary_agent": routing["primary_agent"],
                    "secondary_agent": routing["secondary_agent"],
                    "diagnosis_status": routing["diagnosis_status"],
                    "has_result_to_interpret": routing["has_result_to_interpret"],
                    "plan_status": routing["plan_status"],
                    "location_context": routing["location_context"],
                    "routing_reason": routing["reason"],
                    "routing_backend_used": routing.get("routing_backend_used", ""),
                    "llm_router_success": routing.get("llm_router_success", ""),
                    "llm_router_error": routing.get("llm_router_error", ""),
                    "llm_router_raw_output": json.dumps(
                        routing.get("llm_router_raw_output", {})
                    ),
                }
            )

    output_path = write_csv(rows, OUTPUT_PATH)
    print(output_path)


if __name__ == "__main__":
    main()
