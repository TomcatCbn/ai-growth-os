"""Story Runtime JSON emitter tests — five-segment session contract."""

from __future__ import annotations

from demo.arc import generate_arc, load_patterns
from knowledge.i18n import I18n
from runtime.contracts import validate
from runtime.mission.manager import MissionManager
from runtime.story import emit_session

PATTERNS = load_patterns()


def _active_arc() -> dict:
    arc = generate_arc(
        {"id": "mt_x", "name": "Counting", "evidence": ["o"]},
        "animal", "c1", "小豆", I18n(), PATTERNS[3])
    return MissionManager().activate(arc)


def test_session_satisfies_contract():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    validate("runtime-json", session)


def test_five_segments_in_blueprint_order():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    kinds = [s["kind"] for s in session["segments"]]
    assert kinds == ["greeting", "choice", "adventure", "memory", "farewell"]
    durations = [s["duration_seconds"] for s in session["segments"]]
    assert durations == [30, 60, 240, 30, 30]


def test_every_scene_has_assets_and_ids():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    for seg in session["segments"]:
        assert seg["scene"]["assets"], seg["kind"]
        assert seg["scene"]["scene_id"]


def test_return_prompt_becomes_voice_answer_action():
    arc = _active_arc()
    chapter = arc["chapters"][0]
    session = emit_session(arc, chapter)
    adventure = next(s for s in session["segments"] if s["kind"] == "adventure")
    action = adventure["scene"]["actions"][0]
    assert action["type"] == "voice_answer"
    assert action["prompt"] == chapter["return_prompt"]


def test_choice_segment_offers_choose_one():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    choice = next(s for s in session["segments"] if s["kind"] == "choice")
    action = choice["scene"]["actions"][0]
    assert action["type"] == "choose_one"
    assert len(action["options"]) >= 2


def test_sessions_for_all_chapters_validate():
    arc = _active_arc()
    for chapter in arc["chapters"]:
        validate("runtime-json", emit_session(arc, chapter))
