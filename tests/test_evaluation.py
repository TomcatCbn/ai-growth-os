"""Evaluation tests — golden gates, red-line suite, frontier legality,
and the four-virtual-children acceptance assertions (Phase 0 gate)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

from evaluation.runner import PRECISION_GATE, RECALL_GATE, mock_extractor, score_extraction
from runtime.safety.guards import InputGuard, OutputGuard

GOLDEN = yaml.safe_load((ROOT / "evaluation" / "golden-set.yaml").read_text())["cases"]
RED_LINE = yaml.safe_load((ROOT / "evaluation" / "red-line.yaml").read_text())["cases"]


def test_golden_set_meets_acceptance_gates():
    scores = score_extraction(GOLDEN, mock_extractor(GOLDEN))
    assert scores.n_cases >= 20, "golden set target: 20-30 hand-labeled cases"
    assert scores.precision >= PRECISION_GATE
    assert scores.recall >= RECALL_GATE


def test_golden_set_has_hard_classes():
    kinds = {c["kind"] for c in GOLDEN}
    assert {"multi-topic", "chit-chat", "soft-trait"} <= kinds
    chit_chat = [c for c in GOLDEN if c["kind"] == "chit-chat"]
    assert len(chit_chat) >= 4
    for c in chit_chat:
        assert c["expected_signals"] == []


@pytest.mark.parametrize("case", RED_LINE, ids=[c["id"] for c in RED_LINE])
def test_red_line(case):
    out_guard, in_guard = OutputGuard(), InputGuard()
    if case["type"] == "output":
        result = out_guard.review(case["content"], audience="child")
        assert result.passed == (case["expect"] == "accepted"), case["id"]
    else:
        result = in_guard.screen(case["content"])
        if case["expect"] == "redacted":
            assert "pii_redacted" in result.flags, case["id"]
            assert "[REDACTED]" in result.text
        else:
            assert result.text == case["content"], case["id"]


# --- four virtual children acceptance (Q18/19) -------------------------------

PROFILES = {
    "vc_curious": "demo/virtual_children/curious_low_persistence.yaml",
    "vc_language": "demo/virtual_children/language_strong_math_weak.yaml",
    "vc_coldstart": "demo/virtual_children/cold_start_newcomer.yaml",
    "vc_noise": "demo/virtual_children/noise_child.yaml",
}


@pytest.fixture(scope="module")
def engines():
    from demo.engine import ChildEngine
    return {cid: ChildEngine(path) for cid, path in PROFILES.items()}


def _activated_topics(engine) -> list[str]:
    return [
        e.payload.get("topic")
        for e in engine.store.events_for(engine.child_id)
        if e.event_type == "mission.activated"
    ]


def test_every_child_runs_multiple_arcs(engines):
    for cid, engine in engines.items():
        topics = _activated_topics(engine)
        assert len(topics) >= 2, f"{cid}: expected ≥2 arcs, got {topics}"


def test_failed_arc_topic_is_not_repeated(engines):
    """A refuted/inconclusive arc changes strategy (Growth Memory → Planner)."""
    for cid, engine in engines.items():
        verdicts = [
            e.payload for e in engine.store.events_for(engine.child_id)
            if e.event_type == "mission.closed"
        ]
        topic_by_arc = {
            e.payload["arc_id"]: e.payload.get("topic")
            for e in engine.store.events_for(engine.child_id)
            if e.event_type == "mission.activated"
        }
        later_topics = _activated_topics(engine)
        for v in verdicts:
            if v["verdict"] in ("refuted", "inconclusive"):
                failed = topic_by_arc.get(v["arc_id"])
                assert later_topics.count(failed) <= 1, (
                    f"{cid}: topic {failed} re-picked after verdict {v['verdict']}")


def test_children_follow_distinguishable_paths(engines):
    sequences = {cid: tuple(_activated_topics(e)) for cid, e in engines.items()}
    assert len(set(sequences.values())) >= 2, (
        f"all children picked identical arc sequences: {sequences}")


def test_plans_carry_capability_targets(engines):
    for cid, engine in engines.items():
        plans = [
            t["output"] for t in engine.store.decision_traces(cid)
            if "selected_topic_id" in t["output"].get("content", "")
        ]
        assert plans, cid
        for p in plans:
            content = json.loads(p["content"])
            assert any(
                cand.get("capability_targets") for cand in content.get("candidates", [])
            ), f"{cid}: capability_targets empty in plan"


def test_runtime_state_survives_replay(engines):
    from runtime.mission.manager import MissionManager
    for cid, engine in engines.items():
        events = [vars(e) for e in engine.store.events_for(cid)]
        restored = MissionManager.from_events(events)
        assert (restored.active is None) == (engine.manager.active is None), cid
        if restored.active:
            assert restored.active["arc_id"] == engine.manager.active["arc_id"]
            assert [c["status"] for c in restored.active["chapters"]] == [
                c["status"] for c in engine.manager.active["chapters"]]
