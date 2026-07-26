"""Relationship metrics (Constitution: North Star = child voluntary return).

Honest semantics — a metric may only claim what its events actually prove:

- voluntary_returns: session.started with initiated_by="child" or explicit
  session.returned events. A parent-prompted retelling is NOT a return.
- child_initiated: child.requested_doudou events.
- callback_recognition: partner.callback_recognized / callback_offered —
  did the child light up when Doudou referenced a shared memory?
- trust_level: relationship signals only (returns, recognitions, requests).
  NEVER arc completion — finishing a task is not loving the rabbit.

All metrics are event-log projections — recomputable, no new truth.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any

from ..twin.partner import trust_from_events


def relationship_metrics(events: list[dict]) -> dict[str, Any]:
    session_starts = [
        e for e in events if e.get("event_type") == "session.started"
    ]
    voluntary_returns = sum(
        1 for e in session_starts
        if e["payload"].get("initiated_by") == "child"
    ) + sum(1 for e in events if e.get("event_type") == "session.returned")
    child_requests = sum(
        1 for e in events if e.get("event_type") == "child.requested_doudou")

    offered = sum(
        1 for e in events if e.get("event_type") == "partner.callback_offered")
    recognized = sum(
        1 for e in events
        if e.get("event_type") == "partner.callback_recognized"
        and e["payload"].get("response") == "recognized")

    session_days = sorted({
        e["payload"].get("day")
        for e in session_starts if e["payload"].get("day") is not None
    })
    consecutive = sum(1 for a, b in pairwise(session_days) if b == a + 1)
    opportunities = max(0, len(session_days) - 1)
    return_rate_d2 = round(consecutive / opportunities, 4) if opportunities else 0.0

    return {
        "return_rate_d2": return_rate_d2,
        "voluntary_returns": voluntary_returns,
        "child_initiated": child_requests,
        "callbacks_offered": offered,
        "callbacks_recognized": recognized,
        "callback_recognition_rate": round(recognized / offered, 4) if offered else None,
        "session_days": len(session_days),
        "trust_level": trust_from_events(events),
    }
