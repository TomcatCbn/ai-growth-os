"""Twin-family contract tests (ADR-013) — twin, tendency, growth-pattern,
partner-state, family-model schemas."""

from __future__ import annotations

import pytest

from runtime.contracts import ContractViolation, validate

NOW = "2026-07-26T00:00:00+00:00"


def _twin() -> dict:
    return {
        "child_id": "c1",
        "generated_at": NOW,
        "identity": {"name": "小豆", "age": 5, "stage": "early_childhood"},
        "interests": [{"name": "animal.rabbit", "score": 0.8, "confidence": 0.6}],
        "capabilities": {
            "capability.persistence": {
                "score": 0.4, "trend": "up", "confidence": 0.5,
                "supporting_event_ids": ["ev_1"],
            }
        },
        "learning_pattern": {
            "observations": [{
                "statement": "语言类任务愿意重试，体力任务容易放弃",
                "confidence": 0.5,
                "supporting_event_ids": ["ev_1", "ev_2"],
                "last_reinforced_at": NOW,
            }]
        },
        "relationship": {"partner_id": "doudou_rabbit", "trust_level": 0.4},
        "constraints": ["每次不超过10分钟"],
    }


def _tendency() -> dict:
    return {
        "tendency_id": "td_1",
        "child_id": "c1",
        "trait": "novelty_seeking",
        "evidence": [{
            "event_id": "ev_1",
            "summary": "选择了未知的洞穴小路",
            "observed_at": NOW,
            "direction": "supports",
        }],
        "confidence": 0.6,
        "status": "emerging",
        "created_at": NOW,
        "updated_at": NOW,
    }


def _pattern() -> dict:
    return {
        "pattern_id": "challenge",
        "name_zh": "克服挑战",
        "description": "在逐步升级的挑战中练习坚持",
        "chapter_skeleton": [
            {"role": "hook", "difficulty": 1, "task_pattern": "发现{theme}森林的密码门"},
            {"role": "practice", "difficulty": 2, "task_pattern": "破解密码"},
            {"role": "creation", "difficulty": 3, "task_pattern": "设计自己的密码"},
        ],
        "key_signals": ["孩子主动迁移到新情境"],
        "version": "0.1",
    }


def _partner_state() -> dict:
    return {
        "child_id": "c1",
        "partner_id": "doudou_rabbit",
        "trust_level": 0.4,
        "story_progress": {"completed_arcs": ["arc_1"], "current_thread": "魔法森林"},
        "callbacks_available": [{
            "moment": "小星星", "source_event_id": "ev_1", "used": False,
        }],
        "relationship_memory": [{
            "entry": "给豆豆兔取了名字",
            "confidence": 0.7,
            "supporting_event_ids": ["ev_1"],
            "last_reinforced_at": NOW,
        }],
        "updated_at": NOW,
    }


def _family_model() -> dict:
    return {
        "child_id": "c1",
        "values": ["户外运动优先"],
        "goals": [{
            "goal_id": "fg_1",
            "title": "接触英语",
            "status": "active",
            "created_at": NOW,
        }],
        "constraints": ["每次不超过10分钟"],
        "updated_at": NOW,
    }


CASES = {
    "child-twin": _twin(),
    "tendency": _tendency(),
    "growth-pattern": _pattern(),
    "partner-state": _partner_state(),
    "family-model": _family_model(),
}


@pytest.mark.parametrize("name", list(CASES))
def test_valid_instances_pass(name):
    assert validate(name, CASES[name]) is not None


@pytest.mark.parametrize("name,field", [
    ("child-twin", "identity"),
    ("tendency", "confidence"),
    ("growth-pattern", "chapter_skeleton"),
    ("partner-state", "trust_level"),
    ("family-model", "goals"),
])
def test_missing_required_field_fails(name, field):
    import copy
    instance = copy.deepcopy(CASES[name])
    del instance[field]
    with pytest.raises(ContractViolation):
        validate(name, instance)


def test_insight_entry_requires_provenance():
    import copy
    twin = copy.deepcopy(CASES["child-twin"])
    twin["learning_pattern"]["observations"][0]["supporting_event_ids"] = []
    with pytest.raises(ContractViolation):
        validate("child-twin", twin)


def test_tendency_rejects_unknown_direction():
    import copy
    t = copy.deepcopy(CASES["tendency"])
    t["evidence"][0]["direction"] = "maybe"
    with pytest.raises(ContractViolation):
        validate("tendency", t)


def test_pattern_skeleton_size_limits():
    import copy
    p = copy.deepcopy(CASES["growth-pattern"])
    p["chapter_skeleton"] = p["chapter_skeleton"][:1]
    with pytest.raises(ContractViolation):
        validate("growth-pattern", p)
    p = copy.deepcopy(CASES["growth-pattern"])
    p["chapter_skeleton"] = p["chapter_skeleton"] * 2  # 6 chapters > maxItems 4
    with pytest.raises(ContractViolation):
        validate("growth-pattern", p)


def test_pattern_id_is_closed_vocabulary():
    import copy
    p = copy.deepcopy(CASES["growth-pattern"])
    p["pattern_id"] = "invented_pattern"
    with pytest.raises(ContractViolation):
        validate("growth-pattern", p)
