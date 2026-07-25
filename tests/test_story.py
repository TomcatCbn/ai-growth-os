"""Story Runtime JSON + Scene DSL emitter tests (ADR-014)."""

from __future__ import annotations

from demo.arc import generate_arc, load_patterns
from knowledge.i18n import I18n
from runtime.contracts import validate
from runtime.mission.manager import MissionManager
from runtime.story import emit_session
from runtime.story.emitter import emit_scene

PATTERNS = load_patterns()


def _active_arc() -> dict:
    arc = generate_arc(
        {"id": "mt_x", "name": "Counting", "evidence": ["o"]},
        "animal", "c1", "小豆", I18n(), PATTERNS[3])
    return MissionManager().activate(arc)


def test_session_satisfies_contract():
    arc = _active_arc()
    validate("runtime-json", emit_session(arc, arc["chapters"][0]))


def test_five_segments_in_blueprint_order():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    assert [s["kind"] for s in session["segments"]] == [
        "greeting", "choice", "adventure", "memory", "farewell"]
    assert [s["duration_seconds"] for s in session["segments"]] == [30, 60, 240, 30, 30]


def test_scenes_are_node_sequences():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    for seg in session["segments"]:
        nodes = seg["scene"]["nodes"]
        assert nodes, seg["kind"]
        for n in nodes:
            assert n["type"] in ("dialogue", "choice", "animation", "voice", "reward")


def test_standalone_scene_validates_against_scene_dsl():
    arc = _active_arc()
    scene = emit_scene(arc, arc["chapters"][0], "adventure")
    validate("scene-dsl", scene)
    types = [n["type"] for n in scene["nodes"]]
    assert "voice" in types


def test_return_prompt_becomes_voice_node():
    arc = _active_arc()
    chapter = arc["chapters"][0]
    session = emit_session(arc, chapter)
    adventure = next(s for s in session["segments"] if s["kind"] == "adventure")
    voice_node = next(n for n in adventure["scene"]["nodes"] if n["type"] == "voice")
    assert voice_node["prompt"] == chapter["return_prompt"]


def test_choice_segment_has_choice_node_with_options():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    choice = next(s for s in session["segments"] if s["kind"] == "choice")
    node = next(n for n in choice["scene"]["nodes"] if n["type"] == "choice")
    assert len(node["options"]) >= 2
    assert all("id" in o and "text" in o for o in node["options"])


def test_dialogue_nodes_use_fixed_voice_identity():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    for seg in session["segments"]:
        for n in seg["scene"]["nodes"]:
            if n["type"] == "dialogue" and n.get("speaker") == "doudou":
                assert n["voice"] == "doudou_v1"


def test_memory_segment_has_reward_node():
    arc = _active_arc()
    session = emit_session(arc, arc["chapters"][0])
    memory = next(s for s in session["segments"] if s["kind"] == "memory")
    assert any(n["type"] == "reward" for n in memory["scene"]["nodes"])


def test_sessions_for_all_chapters_validate():
    arc = _active_arc()
    for chapter in arc["chapters"]:
        validate("runtime-json", emit_session(arc, chapter))
