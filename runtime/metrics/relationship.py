"""Relationship metrics (Constitution: North Star = child voluntary return).

Cohort semantics (frozen):
- as_of_date: the observation cutoff — defaults to TODAY (real clock), so
  the metric DECAYS when a child stops returning. Never anchored to the
  last session.
- acquisition cohort: the child's first child_mode session date.
- d2_returned: did the child come back exactly on first+1? (None until
  that day has passed.)
- active_days_d7 / d14: distinct child_mode session dates inside the
  window [as_of−W+1, as_of], divided by the days the child COULD have
  returned (min(W, as_of−first+1)).
- adventure_continuation: next-day session on the SAME arc.
- callback_recognition_rate: recognized / offered, from real player
  interactions only.
- trust_level: relationship signals only — NEVER task completion.

All metrics are event-log projections — recomputable, no new truth.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from ..state.relationship_events import (
    adventure_continuations,
    doudou_requests,
    recognized_callbacks,
    session_dates,
    voluntary_return_days,
)
from ..twin.partner import trust_from_events

WINDOWS = (7, 14)


def _active_day_rate(dates: list[date], first: date, as_of: date, window: int) -> float | None:
    days_available = min(window, (as_of - first).days + 1)
    if days_available <= 0:
        return None
    active = sum(1 for d in dates if 0 <= (as_of - d).days < window)
    return round(active / days_available, 4)


def relationship_metrics(
    events: list[dict], *, as_of: date | None = None
) -> dict[str, Any]:
    as_of = as_of or datetime.now(UTC).date()
    dates = session_dates(events)
    first = dates[0] if dates else None

    d2_returned = None
    if first and (as_of - first).days >= 1:
        d2_returned = (first + timedelta(days=1)) in dates

    rates = {}
    for w in WINDOWS:
        rates[f"active_days_d{w}"] = (
            _active_day_rate(dates, first, as_of, w) if first else None)

    offered = sum(
        1 for e in events if e.get("event_type") == "partner.callback_offered")
    recognized = recognized_callbacks(events)

    return {
        "cohort_first_date": first.isoformat() if first else None,
        "as_of_date": as_of.isoformat(),
        "d2_returned": d2_returned,
        **rates,
        "adventure_continuation": adventure_continuations(events),
        "voluntary_returns": voluntary_return_days(events),
        "child_initiated": doudou_requests(events),
        "callbacks_offered": offered,
        "callbacks_recognized": recognized,
        "callback_recognition_rate": round(recognized / offered, 4) if offered else None,
        "session_days": len(dates),
        "trust_level": trust_from_events(events),
    }
