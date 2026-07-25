"""Twin projection + tendencies tests (ADR-013)."""

from __future__ import annotations

from runtime.contracts import validate
from runtime.events.store import EventStore
from runtime.twin import project_tendencies, project_twin

CHILD = {"child_id": "c1", "name": "小豆", "age": 5, "stage": "early_childhood"}


def _store_with(signals_per_day: list[tuple[int, list[dict]]]) -> EventStore:
    store = EventStore()
    for day, signals in signals_per_day:
        store.append("evidence.signals_extracted", "c1",
                     {"day": day, "signals": signals})
    return store


def _sig(cap: str, strength: float, quote: str = "观察原文") -> dict:
    return {"target_type": "capability", "target_id": cap,
            "signal_strength": strength, "confidence": 0.7, "quote": quote}


def _events(store: EventStore) -> list[dict]:
    return [vars(e) for e in store.events_for("c1")]


def test_twin_satisfies_contract():
    store = _store_with([(1, [_sig("capability.persistence", 0.8)])])
    twin = project_twin(
        child=CHILD, events=_events(store),
        state={"interests": {"animal": 0.8}},
        capabilities={"capability.persistence": {
            "score": 0.4, "topic_derived": None, "direct": 0.4,
            "topic_evidence_count": 0, "direct_evidence_count": 1,
            "confidence": 0.3}})
    validate("child-twin", twin)
    assert twin["identity"]["name"] == "小豆"
    assert twin["capabilities"]["capability.persistence"]["score"] == 0.4


def test_twin_capability_trend_from_events():
    store = _store_with([
        (1, [_sig("capability.persistence", 0.4)]),
        (2, [_sig("capability.persistence", 0.9)]),
    ])
    twin = project_twin(child=CHILD, events=_events(store), state={},
                        capabilities={"capability.persistence": {
                            "score": 0.5, "topic_derived": None, "direct": 0.5,
                            "topic_evidence_count": 0, "direct_evidence_count": 2,
                            "confidence": 0.4}})
    cap = twin["capabilities"]["capability.persistence"]
    assert cap["trend"] == "up"
    assert cap["supporting_event_ids"], "trend must carry its evidence chain"


def test_twin_projection_is_deterministic():
    store = _store_with([(1, [_sig("capability.curiosity", 0.8)])])
    events = _events(store)
    caps = {}
    a = project_twin(child=CHILD, events=events, state={}, capabilities=caps)
    b = project_twin(child=CHILD, events=events, state={}, capabilities=caps)
    stable_a = {k: v for k, v in a.items() if k != "generated_at"}
    stable_b = {k: v for k, v in b.items() if k != "generated_at"}
    assert stable_a == stable_b


def test_tendency_emerges_and_stabilizes():
    store = _store_with([(d, [_sig("capability.curiosity", 0.8, "问了为什么")])
                         for d in (1, 2, 3)])
    tendencies = project_tendencies(_events(store))
    assert len(tendencies) == 1
    t = tendencies[0]
    validate("tendency", t)
    assert t["trait"] == "curious_questioning"
    assert t["status"] == "stable"
    assert all(x["direction"] == "supports" for x in t["evidence"])


def test_tendency_contradiction_marks_stale():
    store = _store_with([
        (1, [_sig("capability.persistence", 0.8)]),
        (2, [_sig("capability.persistence", 0.1)]),
        (3, [_sig("capability.persistence", 0.1)]),
    ])
    t = project_tendencies(_events(store))[0]
    assert t["status"] == "stale"  # history wins
    assert t["confidence"] < 0.5


def test_ambiguous_signals_are_not_evidence():
    store = _store_with([(1, [_sig("capability.curiosity", 0.45)])])
    assert project_tendencies(_events(store)) == []


def test_tendency_ids_are_replay_stable():
    store = _store_with([(1, [_sig("capability.curiosity", 0.8)])])
    events = _events(store)
    assert (project_tendencies(events)[0]["tendency_id"]
            == project_tendencies(events)[0]["tendency_id"])
