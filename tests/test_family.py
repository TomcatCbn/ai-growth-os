"""Family model + mission-score tests — interest bridge, score weights."""

from __future__ import annotations

import json

from runtime.contracts import validate
from runtime.events.store import EventStore
from runtime.llm.base import LLMRequest, LLMResponse
from runtime.planner.planner import GrowthPlanner
from runtime.trace.trace import TrackedProvider
from runtime.twin.family import bridge_goal, build_family_account, build_family_model


def test_bridge_goal_uses_top_interest():
    assert bridge_goal("数学", {"princess": 0.8, "drawing": 0.4}) == "princess·数学"
    assert bridge_goal("数学", {}) == "数学"


def test_family_model_empty_section_is_valid():
    model = build_family_model("c1", None, {})
    validate("family-model", model)
    assert model["goals"] == []


def test_family_model_translates_goals():
    model = build_family_model(
        "c1", {"goals": [{"title": "数学"}], "values": ["阅读优先"]},
        {"princess": 0.8})
    validate("family-model", model)
    assert model["goals"][0]["translated_theme"] == "princess·数学"
    assert model["values"] == ["阅读优先"]


def test_family_account_satisfies_contract():
    account = build_family_account(
        {"child_id": "c1", "name": "朵朵", "age": 4},
        {"goals": [{"title": "数学"}], "values": ["阅读优先"]})
    validate("family-account", account)
    assert account["children"][0]["focus"] == ["数学"]
    assert account["parents"][0]["role"] == "primary"


def test_family_account_multi_child_ready():
    account = build_family_account(
        {"child_id": "c1", "name": "朵朵", "age": 4}, None)
    account["children"].append({"child_id": "c2", "nickname": "弟弟", "age": 3})
    validate("family-account", account)


def test_family_account_minimal_profile():
    account = build_family_account({"child_id": "c1", "name": "小豆", "age": 5}, None)
    validate("family-account", account)
    assert account["children"][0]["focus"] == []


class _CaptureProvider:
    model = "test-capture"

    def __init__(self):
        self.last_user = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_user = request.user
        return LLMResponse(content=json.dumps({
            "candidates": [{"topic_id": "mt_a", "rank": 1, "rationale": "r"}],
            "selected_topic_id": "mt_a", "rationale": "r",
        }), model=self.model)


def test_planner_payload_includes_family_goals():
    provider = _CaptureProvider()
    planner = GrowthPlanner(TrackedProvider(provider, EventStore(), component="test"))
    planner.plan(
        child_id="c1", child_state={}, frontier=[{"topic_id": "mt_a"}],
        recent_evidence=[], family_goals=[{"title": "数学", "status": "active"}])
    payload = json.loads(provider.last_user)
    assert payload["family_goals"] == [{"title": "数学", "status": "active"}]


def test_mock_mission_score_family_component():
    """A topic matching the family goal must outrank an equal one that doesn't."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from demo.mock_llm import MockLLMProvider

    provider = MockLLMProvider()
    user = json.dumps({
        "child_state": {"interests": {}},
        "capabilities": {},
        "growth_memory": {"closed_arcs": []},
        "family_goals": [{"title": "数学", "status": "active"}],
        "frontier": [
            {"topic_id": "mt_math", "name": "One-to-one counting", "subject": "Mathematics",
             "centrality": 0.5, "development_priorities": {}},
            {"topic_id": "mt_other", "name": " unrelated ", "subject": "art",
             "centrality": 0.5, "development_priorities": {}},
        ],
    })
    plan = json.loads(provider.complete(
        LLMRequest(system="You are the Growth Planner", user=user)).content)
    assert plan["selected_topic_id"] == "mt_math"
