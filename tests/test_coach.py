"""Parent Coach tests — contract validity, iron rules, evidence chains."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

from knowledge.i18n import I18n
from runtime.coach import ParentCoach
from runtime.contracts import validate
from runtime.events.store import EventStore

TAXONOMY = yaml.safe_load((ROOT / "world-model" / "capability-taxonomy.yaml").read_text())


def _events_with_signals() -> list[dict]:
    store = EventStore()
    store.append("evidence.signals_extracted", "c1", {"day": 1, "signals": [
        {"target_type": "capability", "target_id": "capability.persistence",
         "signal_strength": 0.5, "confidence": 0.6, "quote": "积木倒了又搭"},
    ]})
    store.append("evidence.signals_extracted", "c1", {"day": 3, "signals": [
        {"target_type": "capability", "target_id": "capability.persistence",
         "signal_strength": 0.9, "confidence": 0.8, "quote": "试了五次终于成功"},
    ]})
    store.append("evidence.signals_extracted", "c1", {"day": 5, "signals": [
        {"target_type": "capability", "target_id": "capability.storytelling",
         "signal_strength": 0.8, "confidence": 0.7, "quote": "自己编了一个故事"},
    ]})
    return [vars(e) for e in store.events_for("c1")]


def test_insight_satisfies_contract():
    coach = ParentCoach(TAXONOMY, I18n())
    insight = coach.build_insight(
        child_id="c1", events=_events_with_signals(), capabilities={})
    validate("parent-insight", insight)
    assert insight["insight_id"].startswith("ins_")
    assert insight["period"]["start"] and insight["period"]["end"]


def test_moments_use_verbatim_quotes():
    coach = ParentCoach(TAXONOMY, I18n())
    events = _events_with_signals()
    insight = coach.build_insight(child_id="c1", events=events, capabilities={})
    quotes = {s["quote"] for e in events for s in e["payload"]["signals"]}
    for m in insight["moments"]:
        for q in m["evidence_quotes"]:
            assert q in quotes


def test_trends_carry_evidence_chain():
    coach = ParentCoach(TAXONOMY, I18n())
    events = _events_with_signals()
    insight = coach.build_insight(child_id="c1", events=events, capabilities={})
    event_ids = {e["event_id"] for e in events}
    assert insight["trends"]
    for t in insight["trends"]:
        assert t["evidence_refs"], "bare number without chain is banned"
        assert set(t["evidence_refs"]) <= event_ids


def test_trend_direction_vs_own_past():
    coach = ParentCoach(TAXONOMY, I18n())
    insight = coach.build_insight(
        child_id="c1", events=_events_with_signals(), capabilities={})
    trend = next(t for t in insight["trends"]
                 if t["capability_id"] == "capability.persistence")
    assert trend["direction"] == "up"


def test_no_comparison_or_diagnosis_language():
    coach = ParentCoach(TAXONOMY, I18n())
    insight = coach.build_insight(
        child_id="c1", events=_events_with_signals(), capabilities={})
    blob = str(insight)
    for banned in ("比其他孩子", "同龄", "落后", "诊断", "排名"):
        assert banned not in blob


def test_empty_events_still_valid():
    coach = ParentCoach(TAXONOMY, I18n())
    insight = coach.build_insight(child_id="c1", events=[], capabilities={})
    validate("parent-insight", insight)


def test_suggestion_targets_weak_priority_capability():
    coach = ParentCoach(TAXONOMY, I18n())
    caps = {"capability.persistence": {
        "score": 0.2, "topic_derived": None, "direct": 0.2,
        "topic_evidence_count": 0, "direct_evidence_count": 3, "confidence": 0.4}}
    insight = coach.build_insight(
        child_id="c1", events=_events_with_signals(), capabilities=caps)
    assert insight["suggestion"]["home_activity"]
    assert insight["suggestion"]["title"].startswith("本周小练习")
