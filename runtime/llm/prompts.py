"""Prompt OS (blueprint Review v5.0): prompts are versioned FILES, loaded by
name — never inline strings buried in components. The active version is
recorded in every decision trace, so any judgment can be traced back to the
exact prompt that produced it.
"""

from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Active versions — bump deliberately, never silently.
PLANNER = "planner_v1"
EXTRACTOR = "extractor_v1"
DOUDOU_PERSONA = "doudou_persona_v1"


def load_prompt(version: str) -> str:
    path = PROMPT_DIR / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"unknown prompt version: {version} ({path})")
    return path.read_text().strip()
