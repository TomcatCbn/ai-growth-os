"""Relationship metrics tests — cohort semantics with as_of cutoff."""

from __future__ import annotations

from datetime import date

from runtime.events.store import EventStore
from runtime.metrics import relationship_metrics


def _events(store: EventStore) -> list[dict]:
    return [vars(e) for e in store.events_for("c1")]


def _start(store, d: str, source: str = "child_mode", arc: str = "a1"):
    store.append("session.started", "c1", {
        "session_id": f"s_{d}_{source}", "date": d,
        "launch_source": source, "arc_id": arc})


def test_parent_prompted_retelling_is_not_a_voluntary_return():
    store = EventStore()
    store.append("evidence.submitted", "c1", {
        "day": 1, "channel": "child_retelling", "raw_text": "家长要求孩子复述"})
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert m["voluntary_returns"] == 0
    assert m["child_initiated"] == 0


def test_d2_cohort_semantics():
    store = EventStore()
    _start(store, "2026-07-20")
    _start(store, "2026-07-21")  # came back exactly next day
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert m["cohort_first_date"] == "2026-07-20"
    assert m["d2_returned"] is True


def test_d2_false_when_no_next_day_return():
    store = EventStore()
    _start(store, "2026-07-20")
    _start(store, "2026-07-25")
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert m["d2_returned"] is False


def test_d2_none_until_next_day_elapsed():
    store = EventStore()
    _start(store, "2026-07-26")
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert m["d2_returned"] is None


def test_window_rates_decay_when_child_stops_returning():
    store = EventStore()
    for d in ["2026-07-01", "2026-07-02"]:
        _start(store, d)
    # as_of anchored TODAY, far after the child stopped → metric decays
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert m["active_days_d7"] == 0.0
    assert m["active_days_d14"] == 0.0
    # but on the day after, it looked great
    m_then = relationship_metrics(_events(store), as_of=date(2026, 7, 3))
    assert m_then["active_days_d7"] == round(2 / 3, 4)


def test_window_denominator_capped_by_days_available():
    store = EventStore()
    _start(store, "2026-07-25")
    _start(store, "2026-07-26")
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    # only 2 days available → 2/2, not 2/7
    assert m["active_days_d7"] == 1.0


def test_parent_preview_never_counts():
    store = EventStore()
    _start(store, "2026-07-25", "parent_preview")
    _start(store, "2026-07-26", "parent_preview")
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert m["voluntary_returns"] == 0
    assert m["session_days"] == 0
    assert m["cohort_first_date"] is None


def test_adventure_continuation_same_arc_next_day():
    store = EventStore()
    _start(store, "2026-07-20", arc="a1")
    _start(store, "2026-07-21", arc="a1")  # continues the same story
    _start(store, "2026-07-25", arc="a2")  # new arc, not a continuation
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert m["adventure_continuation"] == 1


def test_callback_recognition_rate():
    store = EventStore()
    store.append("partner.callback_offered", "c1", {"moment": "m1"})
    store.append("partner.callback_offered", "c1", {"moment": "m2"})
    store.append("partner.callback_recognized", "c1", {
        "moment": "m1", "response": "recognized"})
    store.append("partner.callback_recognized", "c1", {
        "moment": "m2", "response": "ignored"})
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert m["callback_recognition_rate"] == 0.5


def test_no_completion_rate_metrics():
    store = EventStore()
    m = relationship_metrics(_events(store), as_of=date(2026, 7, 26))
    assert "completion_rate" not in m
    assert "learning_minutes" not in m
