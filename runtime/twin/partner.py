"""Partner state projection (ADR-013; blueprint: Partner Relationship Memory).

Events → partner-state contract: trust, story progress, story callbacks
("还记得昨天的小星星吗"), curated relationship memory. Feeds prompts only —
never moves numeric state (ADR-012 boundary).
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..contracts import validate
from ..state.memory import growth_memory_from_events

PARTNER_ID = "doudou_rabbit"


def trust_from_events(events: list[dict]) -> float:
    """Deterministic trust projection: shared arcs build trust, confirmed
    hypotheses build it faster. Recomputable — a view, not a score truth."""
    closed = growth_memory_from_events(events)["closed_arcs"]
    confirmed = sum(1 for a in closed if a["verdict"] == "confirmed")
    return round(min(1.0, 0.1 * len(closed) + 0.1 * confirmed), 4)


def project_partner_state(child_id: str, events: list[dict]) -> dict:
    memory = growth_memory_from_events(events)
    closed = memory["closed_arcs"]

    theme_by_arc: dict[str, str] = {}
    current_thread = ""
    for ev in events:
        if ev.get("event_type") != "mission.activated":
            continue
        p = ev["payload"]
        theme_by_arc[p["arc_id"]] = p.get("theme", "")
    for ev in events:
        if ev.get("event_type") == "mission.activated":
            current_thread = ev["payload"].get("theme", current_thread)

    used_callbacks = {
        ev["payload"].get("moment")
        for ev in events if ev.get("event_type") == "partner.callback_used"
    }

    callbacks = []
    relationship_memory = []
    for arc in closed:
        theme = theme_by_arc.get(arc["arc_id"], "")
        moment = f"{theme}冒险"
        source = arc["supporting_event_ids"][0] if arc["supporting_event_ids"] else ""
        callbacks.append({
            "moment": moment,
            "source_event_id": source,
            "used": moment in used_callbacks,
        })
        if arc["verdict"] == "confirmed":
            relationship_memory.append({
                "entry": f"一起完成了「{theme}」冒险",
                "confidence": 0.6,
                "supporting_event_ids": arc["supporting_event_ids"],
                "last_reinforced_at": "",
            })

    if relationship_memory:
        now = datetime.now(UTC).isoformat()
        for entry in relationship_memory:
            entry["last_reinforced_at"] = now

    state = {
        "child_id": child_id,
        "partner_id": PARTNER_ID,
        "trust_level": trust_from_events(events),
        "story_progress": {
            "completed_arcs": [a["arc_id"] for a in closed],
            "current_thread": current_thread,
        },
        "callbacks_available": callbacks,
        "relationship_memory": relationship_memory,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    validate("partner-state", state)
    return state


def next_callback(partner_state: dict) -> dict | None:
    """The oldest unused callback moment, if any."""
    for cb in partner_state.get("callbacks_available", []):
        if not cb["used"]:
            return cb
    return None
