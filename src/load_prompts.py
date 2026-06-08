from __future__ import annotations

from pathlib import Path


def load_prompts(prompts_dir: str | Path = "prompts") -> dict[str, str]:
    """Load every .txt prompt file, keyed by filename stem."""
    prompt_path = Path(prompts_dir)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompts directory not found: {prompt_path}")

    prompts: dict[str, str] = {}
    for path in sorted(prompt_path.glob("*.txt")):
        prompts[path.stem] = path.read_text(encoding="utf-8").strip()

    return prompts
