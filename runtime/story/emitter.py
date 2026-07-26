"""Story Runtime JSON emitter (ADR-014: Scene DSL node sequences).

Arc chapter → StoryRuntimeSession: five segments (pacing container), each
scene expressed as an ordered node list — backend describes WHAT plays, the
client decides HOW. Deterministic; all text is Output-Guard territory
upstream. Semantic asset refs only (AI never names files).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ..contracts import validate

_DOUDOU = "doudou_v1"

# kind → duration seconds (blueprint: 30s / 1min / 3-5min / 30s / 30s)
_SEGMENT_DURATION = {
    "greeting": 30, "choice": 60, "adventure": 240, "memory": 30, "farewell": 30,
}


def _node(scene_prefix: str, n: int, ntype: str, **fields) -> dict:
    return {"node_id": f"nd_{scene_prefix}_{n}", "type": ntype, **fields}


def _segment(kind: str, arc_id: str, chapter_id: str, nodes: list[dict]) -> dict:
    return {
        "kind": kind,
        "duration_seconds": _SEGMENT_DURATION[kind],
        "scene": {
            "scene_id": f"sc_{arc_id}_{chapter_id}_{kind}",
            "nodes": nodes,
        },
    }


def emit_session(arc: dict, chapter: dict) -> dict:
    """One arc chapter → one five-segment session (contract-validated)."""
    arc_id, chapter_id = arc["arc_id"], chapter["chapter_id"]
    segments = [
        _segment("greeting", arc_id, chapter_id, [
            _node("greet", 1, "animation", asset="character/doudou/action/appear",
                  duration_seconds=3),
            _node("greet", 2, "dialogue", speaker="doudou", text=chapter["narration"],
                  voice=_DOUDOU),
        ]),
        _segment("choice", arc_id, chapter_id, [
            _node("choice", 1, "dialogue", speaker="doudou",
                  text="今天想怎么帮助豆豆兔？", voice=_DOUDOU),
            _node("choice", 2, "choice", prompt="选一个你想试的办法", options=[
                {"id": "opt_doudou", "text": "按照豆豆兔的办法"},
                {"id": "opt_mine", "text": "试试我自己的办法"},
            ]),
        ]),
        _segment("adventure", arc_id, chapter_id, [
            _node("adv", 1, "animation", asset="character/doudou/action/explore",
                  duration_seconds=5),
            _node("adv", 2, "dialogue", speaker="doudou",
                  text=chapter["real_world_task"], voice=_DOUDOU),
            _node("adv", 3, "voice", prompt=chapter["return_prompt"]),
        ]),
        _segment("memory", arc_id, chapter_id, [
            _node("mem", 1, "reward", kind="star",
                  text=f"豆豆兔记住了今天：{arc['growth_hypothesis']['key_signal']}"),
            _node("mem", 2, "animation", asset="character/doudou/emotion/happy",
                  duration_seconds=3),
        ]),
        _segment("farewell", arc_id, chapter_id, [
            _node("bye", 1, "dialogue", speaker="doudou",
                  text="明天豆豆兔还在这里等你，不见不散！", voice=_DOUDOU),
            _node("bye", 2, "animation", asset="character/doudou/action/wave",
                  duration_seconds=3),
        ]),
    ]
    session = {
        "session_id": f"ses_{uuid.uuid4().hex[:10]}",
        "child_id": arc["child_id"],
        "arc_id": arc_id,
        "chapter_id": chapter_id,
        "segments": segments,
        "created_at": datetime.now(UTC).isoformat(),
    }
    validate("runtime-json", session)
    return session


def emit_scene(arc: dict, chapter: dict, segment_kind: str) -> dict:
    """Standalone scene document (scene-dsl contract) for one segment."""
    session = emit_session(arc, chapter)
    scene = next(
        s["scene"] for s in session["segments"] if s["kind"] == segment_kind)
    validate("scene-dsl", scene)
    return scene
