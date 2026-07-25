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
TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "world-model" / "adventure-templates.yaml"


def load_patterns(path: str | Path = PATTERNS_PATH) -> list[dict]:
    doc = yaml.safe_load(Path(path).read_text())
    patterns = doc["patterns"]
    for p in patterns:
        p.setdefault("version", str(doc.get("version", "0.0")))
        validate("growth-pattern", p)
    return patterns


def load_adventure_templates(path: str | Path = TEMPLATES_PATH) -> list[dict]:
    doc = yaml.safe_load(Path(path).read_text())
    templates = doc["templates"]
    for t in templates:
        t.setdefault("version", str(doc.get("version", "0.0")))
        validate("adventure-template", t)
    return templates


def select_template(
    templates: list[dict], pattern_id: str, events: list[dict]
) -> dict | None:
    """Pick the least-recently-used template for the chosen pattern (AI is
    the director, not the author — templates are the human-designed shelf)."""
    recent = [
        e["payload"].get("template_id")
        for e in events if e.get("event_type") == "mission.activated"
    ][-4:]
    candidates = [t for t in templates if t["pattern_id"] == pattern_id]
    if not candidates:
        return None
    return min(candidates, key=lambda t: recent.count(t["template_id"]))


def pace_adjustment(events: list[dict]) -> str:
    """Pace guardrail (blueprint Q43 rule ④): consecutive failures → ease
    off; consecutive successes → push. Returns 'ease' | 'push' | 'steady'."""
    verdicts = [
        a["verdict"] for a in growth_memory_from_events(events)["closed_arcs"]
    ][-2:]
    if len(verdicts) < 2:
        return "steady"
    if all(v == "refuted" for v in verdicts):
        return "ease"
    if all(v == "confirmed" for v in verdicts):
        return "push"
    return "steady"


def select_pattern(
    patterns: list[dict],
    topic_capabilities: list[str],
    events: list[dict],
    pace: str = "steady",
) -> dict:
    """Score = capability fit − recency penalty (variety is a mission-score
    dimension, blueprint: Novelty 10%). The pace guardrail biases difficulty:
    'ease' prefers gentler patterns, 'push' prefers harder ones.
    Deterministic; ties break by library order."""
    recent = [
        e["payload"].get("pattern_id")
        for e in events if e.get("event_type") == "mission.activated"
    ][-3:]

    def max_difficulty(p: dict) -> int:
        return max(c["difficulty"] for c in p["chapter_skeleton"])

    def score(p: dict) -> float:
        suitable = set(p.get("suitable_for", {}).get("capabilities", []))
        fit = len(suitable & set(topic_capabilities))
        s = float(fit - 2 * recent.count(p["pattern_id"]))
        if pace == "ease":
            s -= 0.5 * max_difficulty(p)
        elif pace == "push":
            s += 0.5 * max_difficulty(p)
        return s

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
    callback: dict | None = None,
    template: dict | None = None,
) -> dict:
    """Instantiate a growth pattern into a mission-arc contract object.

    callback: an unused partner-state callback moment — woven into the hook
    narration ("还记得…吗？") so the companion demonstrably remembers.
    template: an AdventureTemplate — the concrete剧本 this arc enacts."""
    checklist = i18n.topic_evidence_zh(topic["id"], topic.get("evidence", []))[:3]
    topic_name = i18n.topic_name(topic["id"], topic["name"])
    chapters = []
    for i, ch in enumerate(pattern["chapter_skeleton"], start=1):
        narration = ch["narration"].format(theme=theme)
        if i == 1 and callback:
            narration = f"还记得我们的{callback['moment']}吗？这一次——" + narration
        chapters.append({
            "chapter_id": f"ch_{i}",
            "index": i,
            "role": ch["role"],
            "title": ch["title"],
            "narration": narration,
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
        "adventure_template_id": template["template_id"] if template else None,
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
