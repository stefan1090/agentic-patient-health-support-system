from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.orchestrator import orchestrate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("user_input")
    parser.add_argument(
        "--routing-backend",
        choices=("rules", "llm"),
        default="rules",
    )
    args = parser.parse_args()

    result = orchestrate(args.user_input, routing_backend=args.routing_backend)
    print(result["scaffold_prompt_output"])


if __name__ == "__main__":
    main()
