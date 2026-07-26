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


def test_return_rate_d2():
    store = EventStore()
    for day, channel in [(1, "free_observation"), (2, "free_observation"),
                         (3, "free_observation"), (10, "free_observation")]:
        store.append("evidence.submitted", "c1", {
            "day": day, "channel": channel, "raw_text": "观察"})
    m = relationship_metrics(_events(store))
    # pairs: (1,2)✓ (2,3)✓ (3,10)✗ → 2/3
    assert m["return_rate_d2"] == round(2 / 3, 4)


def test_adventure_continuation():
    store = EventStore()
    store.append("mission.activated", "c1", {"arc_id": "a1", "day": 1})
    store.append("evidence.submitted", "c1", {
        "day": 2, "channel": "child_retelling", "raw_text": "接着讲昨天的"})
    store.append("evidence.submitted", "c1", {
        "day": 1, "channel": "child_retelling", "raw_text": "当天的"})
    m = relationship_metrics(_events(store))
    assert m["adventure_continuation"] == 1  # only the day-after retelling
