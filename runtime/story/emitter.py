"""Story Runtime JSON emitter (blueprint: five-segment session).

Arc chapter → StoryRuntimeSession contract. Deterministic v1 mapping; the
Orchestrator's adaptation space is scenes/actions, never the observation
checklist (ADR-007). Every child-facing string must already have passed the
Output Guard upstream — the emitter validates the contract, it does not
re-review content.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ..contracts import validate

# Asset-pool refs (blueprint: ~20 base partner videos composed by AI scenes).
_SEGMENT_ASSETS = {
    "greeting": [("vid_doudou_appear", "video")],
    "choice": [("anim_doudou_point", "animation")],
    "adventure": [("vid_doudou_explore", "video"), ("audio_scene_ambient", "audio")],
    "memory": [("vid_doudou_star", "video")],
    "farewell": [("vid_doudou_wave", "video")],
}

# kind → duration seconds (blueprint: 30s / 1min / 3-5min / 30s / 30s)
_SEGMENT_DURATION = {
    "greeting": 30, "choice": 60, "adventure": 240, "memory": 30, "farewell": 30,
}


def _scene(segment: str, arc_id: str, chapter_id: str, narration: str,
           actions: list[dict]) -> dict:
    return {
        "scene_id": f"sc_{arc_id}_{chapter_id}_{segment}",
        "narration": narration,
        "assets": [
            {"asset_id": aid, "kind": kind, "ref": f"assetpool://doudou/{aid}"}
            for aid, kind in _SEGMENT_ASSETS[segment]
        ],
        "actions": actions,
    }


def emit_session(arc: dict, chapter: dict) -> dict:
    """One arc chapter → one five-segment session (contract-validated)."""
    arc_id, chapter_id = arc["arc_id"], chapter["chapter_id"]
    narration = chapter["narration"]
    segments = [
        {
            "kind": "greeting",
            "duration_seconds": _SEGMENT_DURATION["greeting"],
            "scene": _scene("greeting", arc_id, chapter_id, narration, []),
        },
        {
            "kind": "choice",
            "duration_seconds": _SEGMENT_DURATION["choice"],
            "scene": _scene("choice", arc_id, chapter_id,
                            "今天想怎么帮助豆豆兔？",
                            [{
                                "action_id": f"act_{chapter_id}_choice",
                                "type": "choose_one",
                                "prompt": "选一个你想试的办法",
                                "options": ["按照豆豆兔的办法", "试试我自己的办法"],
                            }]),
        },
        {
            "kind": "adventure",
            "duration_seconds": _SEGMENT_DURATION["adventure"],
            "scene": _scene("adventure", arc_id, chapter_id,
                            chapter["real_world_task"],
                            [{
                                "action_id": f"act_{chapter_id}_retell",
                                "type": "voice_answer",
                                "prompt": chapter["return_prompt"],
                            }]),
        },
        {
            "kind": "memory",
            "duration_seconds": _SEGMENT_DURATION["memory"],
            "scene": _scene("memory", arc_id, chapter_id,
                            f"豆豆兔记住了今天：{arc['growth_hypothesis']['key_signal']}",
                            []),
        },
        {
            "kind": "farewell",
            "duration_seconds": _SEGMENT_DURATION["farewell"],
            "scene": _scene("farewell", arc_id, chapter_id,
                            "明天豆豆兔还在这里等你，不见不散！", []),
        },
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
