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


def build_family_account(child: dict, profile_family: dict[str, Any] | None) -> dict:
    """Child profile (+ optional family section) → family-account contract
    (blueprint Q35). Demo profiles describe one child; the account model is
    multi-child ready. Parent input reaches the Twin ONLY as observation
    evidence — this object carries no write path into the Twin."""
    profile_family = profile_family or {}
    account = {
        "family_id": profile_family.get("family_id") or f"fam_{child['child_id']}",
        "parents": profile_family.get("parents") or [
            {"parent_id": f"par_{child['child_id']}", "role": "primary"}
        ],
        "children": [{
            "child_id": child["child_id"],
            "nickname": child["name"],
            "age": child["age"],
            "focus": [g["title"] for g in profile_family.get("goals", [])],
        }],
        "context": {
            "values": profile_family.get("values", []),
            "constraints": profile_family.get("constraints", []),
        },
        "created_at": profile_family.get("created_at") or datetime.now(UTC).isoformat(),
    }
    validate("family-account", account)
    return account
