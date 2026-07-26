"""Relationship metrics tests — honest semantics: metrics may only claim
what their events actually prove."""

from __future__ import annotations

from runtime.events.store import EventStore
from runtime.metrics import relationship_metrics


def _events(store: EventStore) -> list[dict]:
    return [vars(e) for e in store.events_for("c1")]


def test_parent_prompted_retelling_is_not_a_voluntary_return():
    """The review case: '家长要求孩子复述' must NOT count as voluntary."""
    store = EventStore()
    store.append("evidence.submitted", "c1", {
        "day": 1, "channel": "child_retelling", "raw_text": "家长要求孩子复述"})
    m = relationship_metrics(_events(store))
    assert m["voluntary_returns"] == 0
    assert m["child_initiated"] == 0


def test_child_initiated_session_counts():
    store = EventStore()
    store.append("session.started", "c1", {
        "session_id": "s1", "day": 2, "initiated_by": "child"})
    store.append("session.started", "c1", {
        "session_id": "s2", "day": 3, "initiated_by": "parent"})
    store.append("child.requested_doudou", "c1", {"day": 3})
    m = relationship_metrics(_events(store))
    assert m["voluntary_returns"] == 1  # only the child-initiated one
    assert m["child_initiated"] == 1


def test_return_rate_d2_uses_session_days():
    store = EventStore()
    for i, day in enumerate([1, 2, 3, 10]):
        store.append("session.started", "c1", {
            "session_id": f"s{i}", "day": day, "initiated_by": "child"})
    m = relationship_metrics(_events(store))
    assert m["return_rate_d2"] == round(2 / 3, 4)  # (1,2)✓ (2,3)✓ (3,10)✗


def test_callback_recognition_rate():
    store = EventStore()
    store.append("partner.callback_offered", "c1", {"moment": "m1", "arc_id": "a2"})
    store.append("partner.callback_offered", "c1", {"moment": "m2", "arc_id": "a3"})
    store.append("partner.callback_recognized", "c1", {
        "moment": "m1", "response": "recognized"})
    store.append("partner.callback_recognized", "c1", {
        "moment": "m2", "response": "ignored"})
    m = relationship_metrics(_events(store))
    assert m["callbacks_offered"] == 2
    assert m["callbacks_recognized"] == 1
    assert m["callback_recognition_rate"] == 0.5


def test_no_completion_rate_metrics():
    store = EventStore()
    m = relationship_metrics(_events(store))
    assert "completion_rate" not in m
    assert "learning_minutes" not in m
