"""Shared arc templates and target loading for the demo loop.

Single home for CHECKIN_SIGNAL / ARC_TEMPLATES / generate_arc / load_targets —
previously duplicated across run_loop.py and engine.py.
"""

from __future__ import annotations

from knowledge.i18n import I18n

CHECKIN_SIGNAL = {"completed": 0.8, "partial": 0.5, "not_completed": 0.2}

# Observation-point phrasing is intentionally English here (canonical
# knowledge stays English, ADR-005); zh polish arrives with the i18n layer.
ARC_TEMPLATES = [
    ("发现密码", "豆豆兔在{theme}森林深处发现了一扇锁住的门，门上刻着奇怪的图案。",
     "和孩子一起在家里找 3 个有规律的图案（窗帘、地砖、瓷砖），说说规律是什么。",
     "让豆豆兔听听：你们找到了什么图案？它是怎么重复的？"),
    ("破解障碍", "门上的图案原来是一串密码！豆豆兔需要你帮忙找出下一个图案。",
     "用积木/彩珠摆一串 ABAB 规律，让孩子接着摆 3 个；再试试 ABB 规律。",
     "孩子摆的规律是什么？请他教教豆豆兔。"),
    ("打开大门", "最后一道密码最难——这次要孩子自己设计一串密码保护宝藏！",
     "请孩子自己创造一串规律（动作、声音或物品都行），家长来猜规律。",
     "孩子设计的密码是什么？豆豆兔猜对了吗？"),
]


def load_targets(artifact: dict, taxonomy: dict) -> list[dict]:
    targets = [{"id": t["id"], "name": t["name"]} for t in artifact["topics"]]
    for domain in taxonomy["domains"].values():
        for cap in domain["capabilities"]:
            targets.append({"id": cap["id"], "name": cap["name_zh"]})
    return targets


def generate_arc(topic: dict, theme: str, child_id: str, child_name: str, i18n: I18n) -> dict:
    # Observation checklist: human-polished zh where available (ADR-005 §4),
    # canonical English otherwise.
    checklist = i18n.topic_evidence_zh(topic["id"], topic.get("evidence", []))[:3]
    topic_name = i18n.topic_name(topic["id"], topic["name"])
    chapters = []
    for i, (title, narration, task, ret) in enumerate(ARC_TEMPLATES, start=1):
        chapters.append(
            {
                "chapter_id": f"ch_{i}",
                "index": i,
                "title": title,
                "narration": narration.format(theme=theme),
                "real_world_task": task,
                "return_prompt": ret,
                "observation_checklist": checklist,
                "difficulty": i,
                "interaction_mode": "parent_card",
                "default_modality": "voice_story",
                "status": "pending",
            }
        )
    return {
        "child_id": child_id,
        "child_name": child_name,
        "status": "draft",
        "primary_goal": {"topic_id": topic["id"], "capability_ids": []},
        "supporting_goals": [],
        "growth_hypothesis": {
            "statement": f"通过{theme}主题冒险，孩子将在「{topic_name}」上展现可见进步。",
            "expected_mastery_delta": 0.2,
            "key_signal": checklist[0] if checklist else "观察孩子是否主动迁移到新情境",
        },
        "interest_theme": theme,
        "chapters": chapters,
    }
