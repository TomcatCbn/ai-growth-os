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

# Memory importance (blueprint Review v3.0): verdict → base importance.
# >=0.8 long_term, >=0.5 standard, <0.5 fading, <0.1 not stored.
_IMPORTANCE_BY_VERDICT = {"confirmed": 0.9, "inconclusive": 0.6, "refuted": 0.4}
DROP_BELOW = 0.1


def importance_tier(importance: float) -> str:
    if importance >= 0.8:
        return "long_term"
    if importance >= 0.5:
        return "standard"
    return "fading"


def trust_from_events(events: list[dict]) -> float:
    """Trust projection from RELATIONSHIP signals only — voluntary returns,
    recognized callbacks, spontaneous Doudou requests. Arc completion is a
    task metric and never feeds trust (Constitution: relationship first;
    finishing a task is not loving the rabbit)."""
    returns = sum(
        1 for e in events
        if e.get("event_type") == "session.returned"
        or (e.get("event_type") == "session.started"
            and e["payload"].get("initiated_by") == "child"))
    recognized = sum(
        1 for e in events
        if e.get("event_type") == "partner.callback_recognized"
        and e["payload"].get("response") == "recognized")
    requested = sum(
        1 for e in events if e.get("event_type") == "child.requested_doudou")
    return round(min(1.0, 0.1 * returns + 0.15 * recognized + 0.1 * requested), 4)


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
        for ev in events if ev.get("event_type") == "partner.callback_offered"
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
        importance = _IMPORTANCE_BY_VERDICT.get(arc["verdict"], 0.3)
        if importance < DROP_BELOW:
            continue
        relationship_memory.append({
            "entry": f"一起完成了「{theme}」冒险" if arc["verdict"] == "confirmed"
                     else f"一起尝试了「{theme}」冒险",
            "confidence": 0.6,
            "importance": importance,
            "tier": importance_tier(importance),
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
