"""Phase 0 vertical loop tests — session start → player interaction →
honest relationship events. Sessions replay from the event log."""

from __future__ import annotations

import pytest

from demo.engine import ChildEngine
from runtime.contracts import ContractViolation, validate


@pytest.fixture(scope="module")
def engine():
    return ChildEngine("demo/virtual_children/curious_low_persistence.yaml")


def test_start_session_returns_contract_runtime_json(engine):
    session = engine.start_session(launch_source="child_mode")
    validate("runtime-json", session)
    assert session["child_id"] == engine.child_id


def test_start_session_records_honest_launch_source(engine):
    session = engine.start_session(launch_source="parent_preview")
    events = [e for e in engine.store.events_for(engine.child_id)
              if e.event_type == "session.started"]
    last = events[-1]
    assert last.payload["launch_source"] == "parent_preview"
    assert last.payload["session_id"] == session["session_id"]
    assert last.payload["date"], "sessions use real calendar dates"


def test_session_rebuilds_from_event_log(engine):
    session = engine.start_session()
    restored = engine.get_session(session["session_id"])
    assert restored is not None
    assert restored["session_id"] == session["session_id"]
    assert [s["kind"] for s in restored["segments"]] == [
        "greeting", "choice", "adventure", "memory", "farewell"]


def test_interaction_contract_rejects_bad_choice(engine):
    session = engine.start_session()
    with pytest.raises(ContractViolation):
        engine.record_interaction(session["session_id"], "choice",
                                  {"choice_id": "not_a_real_option"})


def test_interaction_contract_rejects_unknown_session(engine):
    with pytest.raises(ContractViolation):
        engine.record_interaction("ses_ghost", "choice",
                                  {"choice_id": "opt_mine"})


def test_interaction_contract_rejects_wrong_node_type(engine):
    session = engine.start_session()
    with pytest.raises(ContractViolation):
        engine.record_interaction(session["session_id"], "dance",
                                  {"answer": "随便"})


def test_voice_interaction_matches_voice_node(engine):
    session = engine.start_session()
    engine.record_interaction(session["session_id"], "voice",
                              {"answer": "我自己摆的规律"})
    types = [e.event_type for e in engine.store.events_for(engine.child_id)]
    assert "session.interaction" in types


def test_legal_choice_interaction_recorded(engine):
    session = engine.start_session()
    engine.record_interaction(session["session_id"], "choice",
                              {"choice_id": "opt_mine"})
    types = [e.event_type for e in engine.store.events_for(engine.child_id)]
    assert "session.interaction" in types


def test_callback_shown_and_recognized_flow(engine):
    """Callback events exist ONLY through real player interactions."""
    session = engine.start_session()
    moment = session.get("callback_moment")
    if moment is None:
        pytest.skip("this arc has no callback woven in")
    engine.record_interaction(session["session_id"], "callback_shown",
                              {"moment": moment})
    engine.record_interaction(session["session_id"], "callback_recognized",
                              {"moment": moment, "response": "recognized"})
    types = [e.event_type for e in engine.store.events_for(engine.child_id)]
    assert "partner.callback_offered" in types
    assert "partner.callback_recognized" in types


def test_callback_moment_mismatch_rejected(engine):
    session = engine.start_session()
    if session.get("callback_moment") is None:
        pytest.skip("this arc has no callback woven in")
    with pytest.raises(ContractViolation):
        engine.record_interaction(session["session_id"], "callback_recognized",
                                  {"moment": "虚构时刻", "response": "recognized"})


def test_bad_launch_source_rejected(engine):
    with pytest.raises(ValueError):
        engine.start_session(launch_source="child")  # old field is gone


def test_session_api_endpoints():
    from fastapi.testclient import TestClient

    from demo.web import app
    client = TestClient(app)
    with client:
        resp = client.post("/api/v1/session/start",
                           data={"child": "vc_curious",
                                 "launch_source": "child_mode"})
        assert resp.status_code == 200
        session = resp.json()
        validate("runtime-json", session)
        sid = session["session_id"]
        resp = client.post("/api/v1/session/interaction",
                           data={"child": "vc_curious", "session_id": sid,
                                 "node_type": "choice",
                                 "data": '{"choice_id": "opt_mine"}'})
        assert resp.json() == {"ok": True}
        resp = client.post("/api/v1/session/interaction",
                           data={"child": "vc_curious", "session_id": sid,
                                 "node_type": "choice",
                                 "data": '{"choice_id": "bogus"}'})
        assert resp.status_code == 422
        resp = client.post("/api/v1/doudou/request",
                           data={"child": "vc_curious"})
        assert resp.json() == {"ok": True}
        resp = client.get("/player", params={"child": "vc_curious"})
        assert resp.status_code == 200
        assert "豆豆兔" in resp.text


def test_assets_exist_on_disk():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for ref in ("character/doudou/emotion/happy",
                "character/doudou/action/appear",
                "character/doudou/action/explore",
                "character/doudou/action/wave"):
        assert (root / "assets" / f"{ref}.svg").exists(), ref
