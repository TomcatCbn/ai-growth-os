"""Relationship metrics (Constitution: North Star = child voluntary return).

Frozen definitions (all dates are REAL calendar dates, ISO strings):
- voluntary return: session.started with launch_source="child_mode" on a
  date AFTER the child's first-ever session date. The first launch is
  acquisition, not return. No session.returned event exists — it would
  double-count.
- return_rate_d2: among adjacent pairs of distinct child_mode session
  dates, the share that are consecutive calendar days.
- return_rate_d7 / d14: distinct dates with a child_mode session inside the
  trailing 7/14-day window ending at the latest session date, divided by
  min(window, span_days+1).
- callback_recognition_rate: recognized / offered, both produced by real
  player interactions only.
- trust_level: relationship signals only — NEVER task completion.

All metrics are event-log projections — recomputable, no new truth.
"""

from __future__ import annotations

from datetime import date
from itertools import pairwise
from typing import Any

from ..twin.partner import trust_from_events

WINDOWS = (7, 14)


def _child_mode_dates(events: list[dict]) -> list[date]:
    dates = set()
    for e in events:
        if e.get("event_type") != "session.started":
            continue
        p = e["payload"]
        if p.get("launch_source") != "child_mode":
            continue
        d = p.get("date")
        if d:
            dates.add(date.fromisoformat(d))
    return sorted(dates)


def _window_rate(dates: list[date], window: int) -> float | None:
    if len(dates) < 2:
        return None  # cannot measure return before a second session day
    latest = dates[-1]
    span = (latest - dates[0]).days + 1
    denominator = min(window, span)
    in_window = sum(1 for d in dates if (latest - d).days < window)
    return round(min(1.0, in_window / denominator), 4)


def relationship_metrics(events: list[dict]) -> dict[str, Any]:
    dates = _child_mode_dates(events)
    voluntary_returns = max(0, len(dates) - 1) if dates else 0

    consecutive = sum(
        1 for a, b in pairwise(dates) if (b - a).days == 1)
    opportunities = max(0, len(dates) - 1)
    return_rate_d2 = round(consecutive / opportunities, 4) if opportunities else None

    child_requests = sum(
        1 for e in events if e.get("event_type") == "child.requested_doudou")
    offered = sum(
        1 for e in events if e.get("event_type") == "partner.callback_offered")
    recognized = sum(
        1 for e in events
        if e.get("event_type") == "partner.callback_recognized"
        and e["payload"].get("response") == "recognized")

    return {
        "return_rate_d2": return_rate_d2,
        "return_rate_d7": _window_rate(dates, 7),
        "return_rate_d14": _window_rate(dates, 14),
        "voluntary_returns": voluntary_returns,
        "child_initiated": child_requests,
        "callbacks_offered": offered,
        "callbacks_recognized": recognized,
        "callback_recognition_rate": round(recognized / offered, 4) if offered else None,
        "session_days": len(dates),
        "first_session_date": dates[0].isoformat() if dates else None,
        "latest_session_date": dates[-1].isoformat() if dates else None,
        "trust_level": trust_from_events(events),
    }
