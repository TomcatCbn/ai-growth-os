"""Relationship event projection — the SINGLE source both the metrics
layer and the partner-trust projection read (no drift by construction).

Population rules (frozen):
- North Star population: session.started with launch_source=="child_mode".
- Callbacks and doudou requests count ONLY when their launch_source is
  child_mode — parent previews never touch metrics or trust.
- Point-in-time: slice_to(events, as_of) drops anything semantically
  AFTER the cutoff, so historical reports can't read the future.
- Defensive dedupe: callback counts are per (session_id, moment), so a
  duplicated write can never push recognition rate above 1.
"""

from __future__ import annotations

from datetime import date, timedelta

CHILD_MODE = "child_mode"


def _semantic_date(e: dict) -> date | None:
    d = e.get("payload", {}).get("date")
    if d:
        return date.fromisoformat(d)
    created = e.get("created_at")
    return date.fromisoformat(created[:10]) if created else None


def slice_to(events: list[dict], as_of: date) -> list[dict]:
    """Point-in-time slice: only events semantically on/before as_of."""
    return [e for e in events if (d := _semantic_date(e)) and d <= as_of]


def child_mode_sessions(events: list[dict]) -> list[dict]:
    """child_mode session.started events, oldest first."""
    sessions = [
        e for e in events
        if e.get("event_type") == "session.started"
        and e["payload"].get("launch_source") == CHILD_MODE
        and e["payload"].get("date")
    ]
    return sorted(sessions, key=lambda e: e["payload"]["date"])


def session_dates(events: list[dict]) -> list[date]:
    """Distinct calendar dates with ≥1 child_mode session, ascending."""
    return sorted({
        date.fromisoformat(e["payload"]["date"])
        for e in child_mode_sessions(events)
    })


def voluntary_return_days(events: list[dict]) -> int:
    """Session days AFTER the first-ever session day (the first day is
    acquisition, not return)."""
    dates = session_dates(events)
    return max(0, len(dates) - 1) if dates else 0


def offered_callbacks(events: list[dict]) -> int:
    """Distinct (session_id, moment) offers, child_mode only."""
    return len({
        (e["payload"].get("session_id"), e["payload"].get("moment"))
        for e in events
        if e.get("event_type") == "partner.callback_offered"
        and e["payload"].get("launch_source") == CHILD_MODE
    })


def recognized_callbacks(events: list[dict]) -> int:
    """Distinct (session_id, moment) recognitions, child_mode only."""
    return len({
        (e["payload"].get("session_id"), e["payload"].get("moment"))
        for e in events
        if e.get("event_type") == "partner.callback_recognized"
        and e["payload"].get("launch_source") == CHILD_MODE
        and e["payload"].get("response") == "recognized"
    })


def doudou_requests(events: list[dict]) -> int:
    return sum(
        1 for e in events
        if e.get("event_type") == "child.requested_doudou"
        and e["payload"].get("launch_source") == CHILD_MODE)


def adventure_continuations(events: list[dict]) -> int:
    """A child_mode session on the day AFTER a session on the SAME arc —
    the child came back to continue the shared story."""
    sessions = child_mode_sessions(events)
    by_date: dict[date, set[str]] = {}
    for e in sessions:
        by_date.setdefault(date.fromisoformat(e["payload"]["date"]), set()).add(
            e["payload"].get("arc_id"))
    count = 0
    for d, arcs in by_date.items():
        prev = by_date.get(d - timedelta(days=1), set())
        if arcs & prev:
            count += 1
    return count
