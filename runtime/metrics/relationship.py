"""Relationship metrics (blueprint Q47: measure the relationship, not completion).

North Star: Child Return Rate — did the child come back on their own?
Deliberately NOT tracked: task completion rate, learning minutes.
All metrics are event-log projections — recomputable, no new truth.

Definitions (frozen):
- return_rate_d2: of all adjacent active-day pairs, the share that are
  CONSECUTIVE days (came back the very next day).
- adventure_continuation: child retellings on a day AFTER an arc was
  activated — the child returned to continue a shared story.
- callbacks_used/offered: partner memory feedback loop usage.
"""

from __future__ import annotations

from itertools import pairwise
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
    arc_days = {
        e["payload"].get("day")
        for e in events
        if e.get("event_type") in ("mission.activated", "mission.chapter_advanced")
        and e["payload"].get("day") is not None
    }
    active_days = sorted({
        e["payload"].get("day")
        for e in events
        if e.get("event_type") == "evidence.submitted" and e["payload"].get("day")
    })

    consecutive = sum(1 for a, b in pairwise(active_days) if b == a + 1)
    opportunities = max(0, len(active_days) - 1)
    return_rate_d2 = round(consecutive / opportunities, 4) if opportunities else 0.0

    continuation = sum(
        1 for e in child_retellings
        if any(d < e["payload"].get("day", 0) for d in arc_days)
    )

    return {
        "return_rate_d2": return_rate_d2,
        "adventure_continuation": continuation,
        "voluntary_returns": len(child_retellings),
        "callbacks_used": len(callbacks_used),
        "callbacks_offered": len(arcs_closed),
        "child_initiated": len(child_retellings),
        "active_days": len(active_days),
        "trust_level": trust_from_events(events),
    }
