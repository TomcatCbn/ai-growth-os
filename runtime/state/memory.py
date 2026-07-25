"""Growth Memory projection (ADR-012) — meta-evidence about which arcs work
for this child, derived from the event log. Read by the Planner so a failed
arc changes future strategy instead of repeating the same pick."""

from __future__ import annotations

from typing import Any


def growth_memory_from_events(events: list[dict]) -> dict[str, Any]:
    """Replay mission lifecycle events into {closed_arcs: [...]}.

    Each entry: {arc_id, topic_id, verdict} where verdict ∈ confirmed /
    refuted / inconclusive (ADR-007 §1)."""
    topic_by_arc: dict[str, str] = {}
    closed: list[dict[str, Any]] = []
    for ev in events:
        etype = ev.get("event_type")
        payload = ev.get("payload", {})
        if etype == "mission.activated":
            arc = payload.get("arc", {})
            topic = payload.get("topic") or arc.get("primary_goal", {}).get("topic_id")
            if topic:
                topic_by_arc[payload["arc_id"]] = topic
        elif etype == "mission.closed":
            arc_id = payload.get("arc_id")
            closed.append({
                "arc_id": arc_id,
                "topic_id": payload.get("topic_id") or topic_by_arc.get(arc_id),
                "verdict": payload.get("verdict"),
            })
    return {"closed_arcs": closed}
