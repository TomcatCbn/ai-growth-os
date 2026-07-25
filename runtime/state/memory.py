"""Growth Memory projection (ADR-012) — meta-evidence about which arcs work
for this child, derived from the event log. Read by the Planner so a failed
arc changes future strategy instead of repeating the same pick."""

from __future__ import annotations

from typing import Any


def growth_memory_from_events(events: list[dict]) -> dict[str, Any]:
    """Replay mission lifecycle events into {closed_arcs: [...]}.

    Each entry: {arc_id, topic_id, verdict, supporting_event_ids} — verdict ∈
    confirmed / refuted / inconclusive (ADR-007 §1). Provenance is mandatory
    (ADR-012 §3): every memory cites the events that produced it."""
    topic_by_arc: dict[str, tuple[str, str]] = {}
    closed: list[dict[str, Any]] = []
    for ev in events:
        etype = ev.get("event_type")
        payload = ev.get("payload", {})
        if etype == "mission.activated":
            arc = payload.get("arc", {})
            topic = payload.get("topic") or arc.get("primary_goal", {}).get("topic_id")
            if topic:
                topic_by_arc[payload["arc_id"]] = (topic, ev.get("event_id", ""))
        elif etype == "mission.closed":
            arc_id = payload.get("arc_id")
            topic, activated_ev = topic_by_arc.get(arc_id, (None, ""))
            closed.append({
                "arc_id": arc_id,
                "topic_id": payload.get("topic_id") or topic,
                "verdict": payload.get("verdict"),
                "supporting_event_ids": [
                    eid for eid in (activated_ev, ev.get("event_id", "")) if eid],
            })
    return {"closed_arcs": closed}
