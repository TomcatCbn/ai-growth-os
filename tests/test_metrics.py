"""Relationship metrics tests."""

from __future__ import annotations

from runtime.events.store import EventStore
from runtime.metrics import relationship_metrics


def _events(store: EventStore) -> list[dict]:
    return [vars(e) for e in store.events_for("c1")]


def test_voluntary_returns_counted():
    store = EventStore()
    store.append("evidence.submitted", "c1", {
        "day": 1, "channel": "child_retelling", "raw_text": "孩子主动讲"})
    store.append("evidence.submitted", "c1", {
        "day": 2, "channel": "free_observation", "raw_text": "家长观察"})
    m = relationship_metrics(_events(store))
    assert m["voluntary_returns"] == 1
    assert m["child_initiated"] == 1
    assert m["active_days"] == 2


def test_no_completion_rate_metrics():
    store = EventStore()
    m = relationship_metrics(_events(store))
    assert "completion_rate" not in m
    assert "learning_minutes" not in m


def test_callback_usage_ratio():
    store = EventStore()
    store.append("mission.closed", "c1", {"arc_id": "a1", "verdict": "confirmed"})
    store.append("partner.callback_used", "c1", {"moment": "m", "arc_id": "a2"})
    m = relationship_metrics(_events(store))
    assert m["callbacks_used"] == 1
    assert m["callbacks_offered"] == 1
