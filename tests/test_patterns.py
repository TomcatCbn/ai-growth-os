"""Growth Pattern Library tests — data validity, selection discipline,
arc instantiation contract."""

from __future__ import annotations

from demo.arc import generate_arc, load_patterns, select_pattern
from knowledge.i18n import I18n
from runtime.contracts import validate
from runtime.events.store import EventStore
from runtime.mission.manager import MissionManager

PATTERNS = load_patterns()


def test_library_has_five_mvp_patterns():
    ids = {p["pattern_id"] for p in PATTERNS}
    assert ids == {"discovery", "build", "help", "challenge", "story_creation"}


def test_patterns_validate_against_contract():
    for p in PATTERNS:
        validate("growth-pattern", p)


def _activation_events(pattern_ids: list[str]) -> list[dict]:
    store = EventStore()
    for i, pid in enumerate(pattern_ids):
        arc = generate_arc(
            {"id": f"mt_{i}", "name": "t", "evidence": ["o"]},
            "animal", "c1", "小豆", I18n(), PATTERNS[0])
        store.append("mission.activated", "c1", {
            "arc_id": f"arc_{i}", "pattern_id": pid, "arc": arc})
    return [vars(e) for e in store.events_for("c1")]


def test_selection_avoids_recently_used_pattern():
    events = _activation_events(["challenge", "challenge"])
    caps = ["capability.pattern_recognition", "capability.persistence"]
    picked = select_pattern(PATTERNS, caps, events)
    # challenge fits best but was just used twice — novelty penalty kicks in
    assert picked["pattern_id"] != "challenge"


def test_selection_prefers_capability_fit_when_fresh():
    picked = select_pattern(
        PATTERNS, ["capability.storytelling"], [])
    assert picked["pattern_id"] == "story_creation"


def test_generated_arc_satisfies_mission_contract():
    for pattern in PATTERNS:
        arc = generate_arc(
            {"id": "mt_x", "name": "Counting", "evidence": ["counts objects"]},
            "animal", "c1", "小豆", I18n(), pattern)
        validate("mission-arc", MissionManager().activate(arc))
        assert arc["pattern_id"] == pattern["pattern_id"]
        roles = [c["role"] for c in arc["chapters"]]
        assert roles[0] == "hook"


def test_arc_hypothesis_uses_pattern_key_signal():
    arc = generate_arc(
        {"id": "mt_x", "name": "Counting", "evidence": []},
        "animal", "c1", "小豆", I18n(), PATTERNS[0])
    assert arc["growth_hypothesis"]["key_signal"] in PATTERNS[0]["key_signals"]
