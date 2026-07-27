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


def _choice_node(session: dict) -> dict:
    for seg in session["segments"]:
        for n in seg["scene"]["nodes"]:
            if n["type"] == "choice":
                return n
    raise AssertionError("no choice node")


def _voice_node(session: dict) -> dict:
    for seg in session["segments"]:
        for n in seg["scene"]["nodes"]:
            if n["type"] == "voice":
                return n
    raise AssertionError("no voice node")


def test_interaction_contract_rejects_bad_choice(engine):
    session = engine.start_session()
    node = _choice_node(session)
    with pytest.raises(ContractViolation):
        engine.record_interaction(session["session_id"], "choice",
                                  {"node_id": node["node_id"],
                                   "choice_id": "not_a_real_option"})


def test_interaction_contract_rejects_unknown_node(engine):
    session = engine.start_session()
    with pytest.raises(ContractViolation):
        engine.record_interaction(session["session_id"], "choice",
                                  {"node_id": "nd_ghost_1",
                                   "choice_id": "opt_mine"})


def test_interaction_contract_rejects_unknown_session(engine):
    with pytest.raises(ContractViolation):
        engine.record_interaction("ses_ghost", "choice",
                                  {"node_id": "nd_x", "choice_id": "opt_mine"})


def test_interaction_contract_rejects_type_mismatch(engine):
    session = engine.start_session()
    voice = _voice_node(session)
    with pytest.raises(ContractViolation):
        engine.record_interaction(session["session_id"], "choice",
                                  {"node_id": voice["node_id"],
                                   "choice_id": "opt_mine"})


def test_interaction_requires_voice_answer(engine):
    session = engine.start_session()
    node = _voice_node(session)
    with pytest.raises(ContractViolation):
        engine.record_interaction(session["session_id"], "voice",
                                  {"node_id": node["node_id"]})


def test_legal_choice_interaction_recorded(engine):
    session = engine.start_session()
    node = _choice_node(session)
    engine.record_interaction(session["session_id"], "choice",
                              {"node_id": node["node_id"],
                               "choice_id": "opt_mine"})
    types = [e.event_type for e in engine.store.events_for(engine.child_id)]
    assert "session.interaction" in types


def test_voice_interaction_matches_voice_node(engine):
    session = engine.start_session()
    node = _voice_node(session)
    engine.record_interaction(session["session_id"], "voice",
                              {"node_id": node["node_id"],
                               "answer": "我自己摆的规律"})
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
    engine.record_interaction(session["session_id"], "callback_answered",
                              {"moment": moment, "response": "recognized"})
    types = [e.event_type for e in engine.store.events_for(engine.child_id)]
    assert "partner.callback_offered" in types
    assert "partner.callback_answered" in types


def test_callback_state_machine(engine):
    """not_shown → shown → recognized|ignored; repeats idempotent,
    out-of-order hard-fails."""
    session = engine.start_session()
    moment = session.get("callback_moment")
    if moment is None:
        pytest.skip("this arc has no callback woven in")
    sid = session["session_id"]

    # recognized before shown → hard violation
    with pytest.raises(ContractViolation):
        engine.record_interaction(sid, "callback_answered",
                                  {"moment": moment, "response": "recognized"})

    engine.record_interaction(sid, "callback_shown", {"moment": moment})
    # repeat shown → idempotent no-op (still exactly one offered event)
    engine.record_interaction(sid, "callback_shown", {"moment": moment})
    engine.record_interaction(sid, "callback_answered",
                              {"moment": moment, "response": "recognized"})
    # repeat answer → idempotent no-op (still exactly one recognized)
    engine.record_interaction(sid, "callback_answered",
                              {"moment": moment, "response": "ignored"})

    events = [e for e in engine.store.events_for(engine.child_id)
              if e.payload.get("session_id") == sid]
    assert sum(1 for e in events
               if e.event_type == "partner.callback_offered") == 1
    answered = [e for e in events
                if e.event_type == "partner.callback_answered"]
    assert len(answered) == 1
    assert answered[0].payload["response"] == "recognized"  # first answer wins


def test_callback_moment_mismatch_rejected(engine):
    session = engine.start_session()
    if session.get("callback_moment") is None:
        pytest.skip("this arc has no callback woven in")
    with pytest.raises(ContractViolation):
        engine.record_interaction(session["session_id"], "callback_answered",
                                  {"moment": "虚构时刻", "response": "recognized"})


def test_bad_launch_source_rejected(engine):
    with pytest.raises(ValueError):
        engine.start_session(launch_source="child")  # old field is gone


def test_session_api_endpoints():
    import re

    from fastapi.testclient import TestClient

    from demo.web import app
    client = TestClient(app)
    with client:
        # source is server-issued: the client presents an entry id
        page = client.get("/player", params={"child": "vc_curious"})
        entry_id = re.search(r'const ENTRY_ID = "([^"]+)"', page.text).group(1)
        resp = client.post("/api/v1/session/start",
                           data={"child": "vc_curious", "entry_id": entry_id})
        assert resp.status_code == 200
        session = resp.json()
        validate("runtime-json", session)
        sid = session["session_id"]
        choice = next(n for seg in session["segments"]
                      for n in seg["scene"]["nodes"] if n["type"] == "choice")
        import json as _json
        resp = client.post("/api/v1/session/interaction",
                           data={"child": "vc_curious", "session_id": sid,
                                 "node_type": "choice",
                                 "data": _json.dumps({
                                     "node_id": choice["node_id"],
                                     "choice_id": "opt_mine"})})
        assert resp.json() == {"ok": True}
        resp = client.post("/api/v1/session/interaction",
                           data={"child": "vc_curious", "session_id": sid,
                                 "node_type": "choice",
                                 "data": _json.dumps({
                                     "node_id": choice["node_id"],
                                     "choice_id": "bogus"})})
        assert resp.status_code == 422
        resp = client.post("/api/v1/doudou/request",
                           data={"child": "vc_curious", "session_id": sid})
        assert resp.json() == {"ok": True}


def test_session_start_rejects_unknown_entry():
    from fastapi.testclient import TestClient

    from demo.web import app
    client = TestClient(app)
    with client:
        resp = client.post("/api/v1/session/start",
                           data={"child": "vc_curious",
                                 "entry_id": "entry_forged"})
        assert resp.status_code == 403
        # a client can no longer claim child_mode directly
        resp = client.post("/api/v1/session/start",
                           data={"child": "vc_curious",
                                 "launch_source": "child_mode"})
        assert resp.status_code == 422  # entry_id missing


def test_preview_entry_yields_parent_preview_session():
    import re

    from fastapi.testclient import TestClient

    from demo.web import app, engines
    client = TestClient(app)
    with client:
        page = client.get("/preview", params={"child": "vc_curious"})
        entry_id = re.search(r'const ENTRY_ID = "([^"]+)"', page.text).group(1)
        resp = client.post("/api/v1/session/start",
                           data={"child": "vc_curious", "entry_id": entry_id})
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        events = [e for e in engines["vc_curious"].store.events_for("vc_curious")
                  if e.event_type == "session.started"
                  and e.payload["session_id"] == sid]
        assert events[0].payload["launch_source"] == "parent_preview"


def test_assets_exist_on_disk():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for ref in ("character/doudou/emotion/happy",
                "character/doudou/action/appear",
                "character/doudou/action/explore",
                "character/doudou/action/wave"):
        assert (root / "assets" / f"{ref}.svg").exists(), ref
