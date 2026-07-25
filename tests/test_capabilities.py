"""Capability derivation tests — ADR-004 aggregation formula, direct-channel
discipline, and planner consumption of development_priority."""

from __future__ import annotations

from runtime.state.capabilities import (
    derive_capabilities,
    development_priorities,
    topic_capabilities,
)

CAP_MAP = {
    "mt_a": [
        {"capability": "capability.pattern_recognition", "relevance": 0.8,
         "evidence_strength": 0.7, "age_fit": 0.9,
         "development_priority": {"4": 0.7, "5": 0.9, "6": 0.8}},
        {"capability": "capability.persistence", "relevance": 0.4,
         "evidence_strength": 0.5, "age_fit": 1.0,
         "development_priority": {"4": 0.6, "5": 0.6, "6": 0.7}},
    ],
    "mt_b": [
        {"capability": "capability.pattern_recognition", "relevance": 0.2,
         "evidence_strength": 0.4, "age_fit": 1.0,
         "development_priority": {"4": 0.7, "5": 0.9, "6": 0.8}},
    ],
}


def test_topic_derived_weighted_mean():
    mastery = {
        "mt_a": {"mastery": 0.8, "confidence": 0.5, "evidence_count": 3},
        "mt_b": {"mastery": 0.2, "confidence": 0.3, "evidence_count": 1},
    }
    view = derive_capabilities(mastery, {}, CAP_MAP)
    # Σ(mastery × relevance × age_fit) / Σ(relevance × age_fit)
    expected = (0.8 * 0.8 * 0.9 + 0.2 * 0.2 * 1.0) / (0.8 * 0.9 + 0.2 * 1.0)
    assert abs(view["capability.pattern_recognition"]["score"] - round(expected, 4)) < 1e-9
    assert view["capability.pattern_recognition"]["topic_evidence_count"] == 4


def test_direct_only_when_no_topic_anchor():
    direct = {"capability.persistence": {"level": 0.6, "confidence": 0.4, "evidence_count": 2}}
    view = derive_capabilities({}, direct, CAP_MAP)
    assert view["capability.persistence"]["score"] == 0.6
    assert view["capability.persistence"]["topic_derived"] is None


def test_fusion_weights_by_evidence_count():
    mastery = {"mt_a": {"mastery": 0.8, "confidence": 0.5, "evidence_count": 3}}
    direct = {"capability.persistence": {"level": 0.2, "confidence": 0.4, "evidence_count": 1}}
    view = derive_capabilities(mastery, direct, CAP_MAP)
    # topic-derived for persistence: 0.8 (single edge); fused = (3×0.8 + 1×0.2)/4
    assert view["capability.persistence"]["score"] == round((3 * 0.8 + 1 * 0.2) / 4, 4)


def test_development_priority_age_banded():
    prios = development_priorities(CAP_MAP, "mt_a", age=5)
    assert prios["capability.pattern_recognition"] == 0.9
    prios4 = development_priorities(CAP_MAP, "mt_a", age=4)
    assert prios4["capability.pattern_recognition"] == 0.7


def test_age_band_clamped_to_mvp():
    prios = development_priorities(CAP_MAP, "mt_a", age=9)
    assert prios["capability.pattern_recognition"] == 0.8  # clamped to band 6


def test_topic_capabilities_lookup():
    assert topic_capabilities("mt_a", CAP_MAP) == [
        "capability.pattern_recognition", "capability.persistence"]
    assert topic_capabilities("mt_unknown", CAP_MAP) == []
