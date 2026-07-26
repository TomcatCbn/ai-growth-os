"""P1 defect tests — screening coverage, trace ordering, evidence contract."""

from __future__ import annotations

import pytest

from runtime.contracts import ContractViolation
from runtime.events.store import EventStore
from runtime.llm.base import LLMRequest, LLMResponse
from runtime.trace.trace import TrackedProvider


def test_append_safety_screens_payload():
    store = EventStore()
    ev = store.append_safety("safety.output_rejected", "c1", {
        "flags": ["red_line"], "excerpt": "联系13812345678"})
    assert "13812345678" not in str(ev.payload)


def test_trace_rationale_is_screened():
    store = EventStore()
    store.trace("test", input_snapshot={}, output={},
                child_id="c1", rationale="电话13812345678")
    traces = store.decision_traces("c1")
    assert "13812345678" not in traces[0]["rationale"]


class _BadProvider:
    model = "bad"

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content='{"wrong": "shape"}', model=self.model)


class _GoodProvider:
    model = "good"

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content='{"signals": []}', model=self.model)


SCHEMA = {
    "type": "object",
    "required": ["signals"],
    "properties": {"signals": {"type": "array"}},
}


def test_invalid_response_raises_before_trace():
    store = EventStore()
    llm = TrackedProvider(_BadProvider(), store, component="test")
    with pytest.raises(ContractViolation):
        llm.complete(LLMRequest(system="s", user="u", response_schema=SCHEMA),
                     child_id="c1")
    assert store.decision_traces("c1") == [], \
        "invalid judgment must not be written as a decision trace"


def test_non_json_response_raises_before_trace():
    class NonJson:
        model = "nj"

        def complete(self, request):
            return LLMResponse(content="not json at all", model=self.model)

    store = EventStore()
    llm = TrackedProvider(NonJson(), store, component="test")
    with pytest.raises(ContractViolation):
        llm.complete(LLMRequest(system="s", user="u", response_schema=SCHEMA),
                     child_id="c1")
    assert store.decision_traces("c1") == []


def test_valid_response_traces_normally():
    store = EventStore()
    llm = TrackedProvider(_GoodProvider(), store, component="test")
    _, trace_id = llm.complete(
        LLMRequest(system="s", user="u", response_schema=SCHEMA), child_id="c1")
    assert trace_id
    assert len(store.decision_traces("c1")) == 1


def test_evidence_event_is_full_contract_object():
    from demo.engine import ChildEngine
    engine = ChildEngine("demo/virtual_children/noise_child.yaml")
    from runtime.contracts import validate
    for e in engine.store.events_for(engine.child_id):
        if e.event_type == "evidence.submitted":
            validate("evidence", e.payload)
            assert e.payload["evidence_id"] == e.event_id
            break
    else:
        pytest.fail("no evidence.submitted event found")


def test_live_mode_rejects_mock_capability_map():
    from demo.engine import ChildEngine
    from runtime.state.capabilities import UnadjudicatedAssetError
    with pytest.raises(UnadjudicatedAssetError):
        ChildEngine("demo/virtual_children/noise_child.yaml", live=True)
