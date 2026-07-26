"""Relationship event projection — the SINGLE source both the metrics
layer and the partner-trust projection read (no drift by construction).

North Star population: session.started events with
launch_source == "child_mode". Parent previews are excluded everywhere.
"""

from __future__ import annotations

from datetime import date


def child_mode_sessions(events: list[dict]) -> list[dict]:
    """child_mode session.started events, oldest first."""
    sessions = [
        e for e in events
        if e.get("event_type") == "session.started"
        and e["payload"].get("launch_source") == "child_mode"
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


def recognized_callbacks(events: list[dict]) -> int:
    return sum(
        1 for e in events
        if e.get("event_type") == "partner.callback_recognized"
        and e["payload"].get("response") == "recognized")


def doudou_requests(events: list[dict]) -> int:
    return sum(
        1 for e in events if e.get("event_type") == "child.requested_doudou")


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
        from datetime import timedelta
        prev = by_date.get(d - timedelta(days=1), set())
        if arcs & prev:
            count += 1
    return count
