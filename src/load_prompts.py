from __future__ import annotations

import re
from pathlib import Path


def load_prompts(prompts_dir: str | Path = "prompts") -> dict[str, str]:
    """Load every .txt prompt file, keyed by filename stem."""
    prompt_path = Path(prompts_dir)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompts directory not found: {prompt_path}")

    prompts: dict[str, str] = {}
    for path in sorted(prompt_path.glob("*.txt")):
        prompts[prompt_key(path)] = path.read_text(encoding="utf-8").strip()

    return prompts


def prompt_key(path: Path) -> str:
    """Map ordered prompt filenames back to stable agent labels."""
    return re.sub(r"^a\d+_", "", path.stem)
