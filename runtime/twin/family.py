"""Family Model (blueprint: values/goals, never 'control').

Parent goals reach the child ONLY through the interest bridge:
goal + top interest → adventure theme (英语目标 + 喜欢动物 → 动物园管理员).
Priority order: safety > child autonomy > growth goals > parent expectations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from ..contracts import validate


def bridge_goal(title: str, interests: dict[str, float]) -> str:
    """Interest bridge: translate a parent goal into an adventure theme
    anchored in the child's top interest."""
    if not interests:
        return title
    top = max(interests, key=interests.get).split(".")[-1]
    return f"{top}·{title}"


def build_family_model(
    child_id: str,
    profile_family: dict[str, Any] | None,
    interests: dict[str, float],
) -> dict:
    """Profile family section → family-model contract. Missing section yields
    an empty-but-valid model (no goals is a fact, not an error)."""
    now = datetime.now(UTC).isoformat()
    profile_family = profile_family or {}
    goals = []
    for g in profile_family.get("goals", []):
        goals.append({
            "goal_id": g.get("goal_id") or f"fg_{uuid.uuid4().hex[:8]}",
            "title": g["title"],
            "raw_text": g.get("raw_text", ""),
            "translated_theme": bridge_goal(g["title"], interests),
            "status": g.get("status", "active"),
            "created_at": g.get("created_at", now),
        })
    model = {
        "child_id": child_id,
        "values": profile_family.get("values", []),
        "goals": goals,
        "constraints": profile_family.get("constraints", []),
        "updated_at": now,
    }
    validate("family-model", model)
    return model
