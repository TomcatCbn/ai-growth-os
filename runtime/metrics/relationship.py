"""Relationship metrics (blueprint: measure the relationship, not completion).

Deliberately NOT tracked: task completion rate, learning minutes.
Tracked: voluntary returns (did the child come back on their own), partner
memory feedback (callbacks offered vs. used), child-initiated interaction,
trust projection. All are event-log projections — recomputable, no new truth.
"""

from __future__ import annotations

from typing import Any

from ..twin.partner import trust_from_events


def relationship_metrics(events: list[dict]) -> dict[str, Any]:
    child_retellings = [
        e for e in events
        if e.get("event_type") == "evidence.submitted"
        and e["payload"].get("channel") == "child_retelling"
    ]
    callbacks_used = [
        e for e in events if e.get("event_type") == "partner.callback_used"
    ]
    arcs_closed = [
        e for e in events if e.get("event_type") == "mission.closed"
    ]
    active_days = {
        e["payload"].get("day")
        for e in events
        if e.get("event_type") == "evidence.submitted" and e["payload"].get("day")
    }
    return {
        "voluntary_returns": len(child_retellings),
        "callbacks_used": len(callbacks_used),
        "callbacks_offered": len(arcs_closed),
        "child_initiated": len(child_retellings),
        "active_days": len(active_days),
        "trust_level": trust_from_events(events),
    }
