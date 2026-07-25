"""Growth arc instantiation — pattern library × topic × child interests.

An arc = GrowthPattern template × topic × child theme (blueprint Q18:
template library + AI personalization). Patterns are data
(world-model/growth-patterns.yaml), validated against the growth-pattern
contract at load. Pattern selection is code (capability fit − recent use),
never LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from knowledge.i18n import I18n
from runtime.contracts import validate
from runtime.state.memory import growth_memory_from_events

CHECKIN_SIGNAL = {"completed": 0.8, "partial": 0.5, "not_completed": 0.2}

PATTERNS_PATH = Path(__file__).resolve().parent.parent / "world-model" / "growth-patterns.yaml"


def load_patterns(path: str | Path = PATTERNS_PATH) -> list[dict]:
    doc = yaml.safe_load(Path(path).read_text())
    patterns = doc["patterns"]
    for p in patterns:
        p.setdefault("version", str(doc.get("version", "0.0")))
        validate("growth-pattern", p)
    return patterns


def select_pattern(
    patterns: list[dict],
    topic_capabilities: list[str],
    events: list[dict],
) -> dict:
    """Score = capability fit − recency penalty (variety is a mission-score
    dimension, blueprint: Novelty 10%). Deterministic; ties break by library
    order."""
    recent = [
        e["payload"].get("pattern_id")
        for e in events if e.get("event_type") == "mission.activated"
    ][-3:]

    def score(p: dict) -> int:
        suitable = set(p.get("suitable_for", {}).get("capabilities", []))
        fit = len(suitable & set(topic_capabilities))
        return fit - 2 * recent.count(p["pattern_id"])

    return max(patterns, key=score)


def load_targets(artifact: dict, taxonomy: dict) -> list[dict]:
    targets = [{"id": t["id"], "name": t["name"]} for t in artifact["topics"]]
    for domain in taxonomy["domains"].values():
        for cap in domain["capabilities"]:
            targets.append({"id": cap["id"], "name": cap["name_zh"]})
    return targets


def generate_arc(
    topic: dict,
    theme: str,
    child_id: str,
    child_name: str,
    i18n: I18n,
    pattern: dict,
) -> dict:
    """Instantiate a growth pattern into a mission-arc contract object."""
    checklist = i18n.topic_evidence_zh(topic["id"], topic.get("evidence", []))[:3]
    topic_name = i18n.topic_name(topic["id"], topic["name"])
    chapters = []
    for i, ch in enumerate(pattern["chapter_skeleton"], start=1):
        chapters.append({
            "chapter_id": f"ch_{i}",
            "index": i,
            "role": ch["role"],
            "title": ch["title"],
            "narration": ch["narration"].format(theme=theme),
            "real_world_task": ch["task_pattern"].format(theme=theme),
            "return_prompt": ch["return_prompt"],
            "observation_checklist": checklist,
            "difficulty": ch["difficulty"],
            "interaction_mode": "parent_card",
            "default_modality": "voice_story",
            "status": "pending",
        })
    return {
        "child_id": child_id,
        "child_name": child_name,
        "pattern_id": pattern["pattern_id"],
        "status": "draft",
        "primary_goal": {"topic_id": topic["id"], "capability_ids": []},
        "supporting_goals": [],
        "growth_hypothesis": {
            "statement": (
                f"通过「{pattern['name_zh']}」模式的{theme}主题冒险，"
                f"孩子将在「{topic_name}」上展现可见进步。"),
            "expected_mastery_delta": 0.2,
            "key_signal": pattern["key_signals"][0],
        },
        "interest_theme": theme,
        "chapters": chapters,
    }


def recently_used_patterns(events: list[dict]) -> list[str]:
    """Pattern ids of closed arcs, oldest first (for novelty accounting)."""
    return [
        a.get("pattern_id")
        for a in growth_memory_from_events(events)["closed_arcs"]
        if a.get("pattern_id")
    ]


def arc_pattern_summary(arc: dict) -> dict[str, Any]:
    return {"pattern_id": arc.get("pattern_id"), "theme": arc.get("interest_theme")}
