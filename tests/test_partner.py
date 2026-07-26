"""Partner state tests — trust projection, callbacks, contract validity."""

from __future__ import annotations

from demo.arc import generate_arc, load_patterns
from knowledge.i18n import I18n
from runtime.contracts import validate
from runtime.events.store import EventStore
from runtime.mission.manager import MissionManager
from runtime.twin import next_callback, project_partner_state
from runtime.twin.partner import trust_from_events

PATTERNS = load_patterns()


def _arc_lifecycle(store: EventStore, theme: str, verdict_status: str = "completed"):
    mgr = MissionManager()
    arc = mgr.activate(generate_arc(
        {"id": "mt_x", "name": "t", "evidence": ["o"]},
        theme, "c1", "小豆", I18n(), PATTERNS[3]))
    store.append("mission.activated", "c1", {
        "arc_id": arc["arc_id"], "topic": "mt_x", "theme": theme,
        "pattern_id": "challenge", "arc": arc})
    closed = mgr.close(verdict_status)
    store.append("mission.closed", "c1", {
        "arc_id": closed["arc_id"], "verdict": closed["hypothesis_verdict"],
        "status": closed["status"]})


def _events(store: EventStore) -> list[dict]:
    return [vars(e) for e in store.events_for("c1")]


def test_partner_state_satisfies_contract():
    store = EventStore()
    _arc_lifecycle(store, "animal")
    state = project_partner_state("c1", _events(store))
    validate("partner-state", state)
    assert state["partner_id"] == "doudou_rabbit"
    assert state["story_progress"]["completed_arcs"]


def test_trust_grows_with_relationship_signals_not_completion():
    """Arc completion must NOT move trust; relationship signals must."""
    store = EventStore()
    _arc_lifecycle(store, "animal", "completed")
    _arc_lifecycle(store, "dinosaur", "completed")
    assert trust_from_events(_events(store)) == 0.0, \
        "completed arcs are task metrics, not relationship"
    store.append("session.started", "c1", {
        "session_id": "s1", "date": "2026-07-20", "launch_source": "child_mode"})
    store.append("session.started", "c1", {
        "session_id": "s2", "date": "2026-07-21", "launch_source": "child_mode"})
    store.append("partner.callback_recognized", "c1", {
        "moment": "animal冒险", "response": "recognized"})
    assert trust_from_events(_events(store)) == 0.25  # 0.1 return + 0.15 recognized


def test_completed_arc_offers_callback():
    store = EventStore()
    _arc_lifecycle(store, "animal")
    state = project_partner_state("c1", _events(store))
    cb = next_callback(state)
    assert cb is not None
    assert "animal" in cb["moment"]
    assert cb["used"] is False


def test_callback_marks_used_after_offering():
    store = EventStore()
    _arc_lifecycle(store, "animal")
    store.append("partner.callback_offered", "c1", {
        "moment": "animal冒险", "source_event_id": "ev_x", "arc_id": "arc_y"})
    state = project_partner_state("c1", _events(store))
    assert next_callback(state) is None
    assert state["callbacks_available"][0]["used"] is True


def test_relationship_memory_has_provenance():
    store = EventStore()
    _arc_lifecycle(store, "animal", "completed")
    state = project_partner_state("c1", _events(store))
    assert state["relationship_memory"]
    for entry in state["relationship_memory"]:
        assert entry["supporting_event_ids"]
        assert entry["last_reinforced_at"]


def test_memory_importance_tiers():
    store = EventStore()
    _arc_lifecycle(store, "animal", "completed")   # confirmed → 0.9 long_term
    _arc_lifecycle(store, "dinosaur", "partial")    # inconclusive → 0.6 standard
    state = project_partner_state("c1", _events(store))
    by_tier = {e["tier"] for e in state["relationship_memory"]}
    assert "long_term" in by_tier and "standard" in by_tier
    for e in state["relationship_memory"]:
        assert e["importance"] >= 0.1
    confirmed = next(e for e in state["relationship_memory"]
                     if e["importance"] == 0.9)
    assert confirmed["tier"] == "long_term"


def test_callback_woven_into_hook_narration():
    arc = generate_arc(
        {"id": "mt_x", "name": "t", "evidence": ["o"]},
        "dinosaur", "c1", "小豆", I18n(), PATTERNS[3],
        callback={"moment": "animal冒险", "source_event_id": "ev_1", "used": False})
    assert arc["chapters"][0]["narration"].startswith("还记得我们的animal冒险吗？")
    validate("mission-arc", MissionManager().activate(arc))
