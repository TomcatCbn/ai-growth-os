"""Replay tests — runtime state and growth state rebuild from the event log."""

from __future__ import annotations

from runtime.events.store import EventStore
from runtime.mission.manager import MissionManager
from runtime.state.reducer import reduce_events


def _arc(arc_id: str = "arc_1") -> dict:
    chapter = {
        "chapter_id": "ch_1", "index": 1, "title": "t1", "narration": "n",
        "real_world_task": "t", "return_prompt": "p",
        "observation_checklist": ["o"], "difficulty": 1, "status": "pending",
    }
    return {
        "arc_id": arc_id, "child_id": "c1", "status": "draft",
        "primary_goal": {"topic_id": "mt_a"},
        "growth_hypothesis": {"statement": "s", "key_signal": "k"},
        "chapters": [
            chapter,
            dict(chapter, chapter_id="ch_2", index=2),
            dict(chapter, chapter_id="ch_3", index=3),
        ],
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _lifecycle_events(store: EventStore) -> None:
    mgr = MissionManager()
    arc = mgr.activate(_arc())
    store.append("mission.activated", "c1", {
        "arc_id": arc["arc_id"], "arc": arc, "activated_at": mgr.activated_at})
    ch2 = mgr.advance_chapter()
    store.append("mission.chapter_advanced", "c1", {
        "arc_id": arc["arc_id"], "chapter_id": ch2["chapter_id"],
        "checkin_status": "partial"})
    ch3 = mgr.advance_chapter()
    store.append("mission.chapter_advanced", "c1", {
        "arc_id": arc["arc_id"], "chapter_id": ch3["chapter_id"],
        "checkin_status": "partial"})
    closed = mgr.close("completed")
    store.append("mission.closed", "c1", {
        "arc_id": closed["arc_id"], "verdict": closed["hypothesis_verdict"],
        "status": closed["status"]})
    arc2 = mgr.activate(_arc("arc_2"))
    store.append("mission.activated", "c1", {
        "arc_id": arc2["arc_id"], "arc": arc2, "activated_at": mgr.activated_at})


def test_advance_chapter_walks_the_arc():
    mgr = MissionManager()
    mgr.activate(_arc())
    ch2 = mgr.advance_chapter()
    assert ch2["chapter_id"] == "ch_2"
    assert [c["status"] for c in mgr.active["chapters"]] == ["done", "active", "pending"]
    mgr.advance_chapter()
    assert [c["status"] for c in mgr.active["chapters"]] == ["done", "done", "active"]


def test_advance_past_last_chapter_raises():
    mgr = MissionManager()
    mgr.activate(_arc())
    mgr.advance_chapter()
    mgr.advance_chapter()
    try:
        mgr.advance_chapter()
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_replay_restores_exactly_one_active_mission():
    store = EventStore()
    _lifecycle_events(store)
    events = [vars(e) for e in store.events_for("c1")]
    mgr = MissionManager.from_events(events)
    assert mgr.active is not None
    assert mgr.active["arc_id"] == "arc_2"
    assert mgr.active["status"] == "active"
    assert mgr.active["chapters"][0]["status"] == "active"


def test_replay_restores_chapter_progress():
    store = EventStore()
    _lifecycle_events(store)
    # drop the closing + second activation: replay must show chapter 3 active
    events = [vars(e) for e in store.events_for("c1")][:3]
    mgr = MissionManager.from_events(events)
    statuses = [c["status"] for c in mgr.active["chapters"]]
    assert statuses == ["done", "done", "active"]


def test_restart_does_not_reinject_timeline(tmp_path):
    """Restarting with a persistent db must not duplicate profile timeline
    evidence — duplicates would poison Twin, trust, and return metrics."""
    from demo.engine import ChildEngine
    db = str(tmp_path / "engine.db")
    first = ChildEngine("demo/virtual_children/curious_low_persistence.yaml", db=db)
    n1 = len(first.store.events_for(first.child_id))
    second = ChildEngine("demo/virtual_children/curious_low_persistence.yaml", db=db)
    n2 = len(second.store.events_for(second.child_id))
    assert n1 == n2, f"re-injection: {n1} events, then {n2} after restart"


def test_growth_state_replay_is_deterministic():
    store = EventStore()
    store.append("evidence.signals_extracted", "c1", {"day": 1, "signals": [
        {"target_type": "topic", "target_id": "mt_a",
         "signal_strength": 0.8, "confidence": 0.7, "quote": "q"},
    ]})
    store.append("evidence.signals_extracted", "c1", {"day": 2, "signals": [
        {"target_type": "topic", "target_id": "mt_a",
         "signal_strength": 0.8, "confidence": 0.7, "quote": "q"},
    ]})
    events = [vars(e) for e in store.events_for("c1")]
    first = reduce_events(events)
    second = reduce_events(events)
    assert first == second
    assert first["topic_mastery"]["mt_a"]["evidence_count"] == 2
