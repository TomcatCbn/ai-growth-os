"""Relationship metrics tests — honest semantics, real calendar dates."""

from __future__ import annotations

from runtime.events.store import EventStore
from runtime.metrics import relationship_metrics


def _events(store: EventStore) -> list[dict]:
    return [vars(e) for e in store.events_for("c1")]


def _start(store, date: str, source: str = "child_mode", sid: str | None = None):
    store.append("session.started", "c1", {
        "session_id": sid or f"s_{date}_{source}", "date": date,
        "launch_source": source})


def test_parent_prompted_retelling_is_not_a_voluntary_return():
    """The review case: '家长要求孩子复述' must NOT count as voluntary."""
    store = EventStore()
    store.append("evidence.submitted", "c1", {
        "day": 1, "channel": "child_retelling", "raw_text": "家长要求孩子复述"})
    m = relationship_metrics(_events(store))
    assert m["voluntary_returns"] == 0
    assert m["child_initiated"] == 0


def test_first_session_is_acquisition_not_return():
    store = EventStore()
    _start(store, "2026-07-20")
    m = relationship_metrics(_events(store))
    assert m["voluntary_returns"] == 0
    assert m["return_rate_d2"] is None
    _start(store, "2026-07-21")
    m = relationship_metrics(_events(store))
    assert m["voluntary_returns"] == 1


def test_parent_preview_never_counts():
    store = EventStore()
    _start(store, "2026-07-20", "parent_preview")
    _start(store, "2026-07-21", "parent_preview")
    m = relationship_metrics(_events(store))
    assert m["voluntary_returns"] == 0
    assert m["session_days"] == 0


def test_return_rate_d2_uses_real_calendar_dates():
    store = EventStore()
    for d in ["2026-07-20", "2026-07-21", "2026-07-22", "2026-07-30"]:
        _start(store, d)
    m = relationship_metrics(_events(store))
    assert m["return_rate_d2"] == round(2 / 3, 4)


def test_return_rate_d7_d14_windows():
    store = EventStore()
    for d in ["2026-07-01", "2026-07-02", "2026-07-20", "2026-07-21"]:
        _start(store, d)
    m = relationship_metrics(_events(store))
    # window ends at latest (07-21); span = 21 days → denominator 7 / 14
    assert m["return_rate_d7"] == round(2 / 7, 4)
    assert m["return_rate_d14"] == round(2 / 14, 4)


def test_callback_recognition_rate():
    store = EventStore()
    store.append("partner.callback_offered", "c1", {"moment": "m1"})
    store.append("partner.callback_offered", "c1", {"moment": "m2"})
    store.append("partner.callback_recognized", "c1", {
        "moment": "m1", "response": "recognized"})
    store.append("partner.callback_recognized", "c1", {
        "moment": "m2", "response": "ignored"})
    m = relationship_metrics(_events(store))
    assert m["callback_recognition_rate"] == 0.5


def test_no_completion_rate_metrics():
    store = EventStore()
    m = relationship_metrics(_events(store))
    assert "completion_rate" not in m
    assert "learning_minutes" not in m
