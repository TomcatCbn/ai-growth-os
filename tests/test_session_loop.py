"""Phase 0 vertical loop tests — session start → player interaction →
honest relationship events."""

from __future__ import annotations

import pytest

from demo.engine import ChildEngine
from runtime.contracts import validate


@pytest.fixture(scope="module")
def engine():
    return ChildEngine("demo/virtual_children/curious_low_persistence.yaml")


def test_start_session_returns_contract_runtime_json(engine):
    session = engine.start_session(initiated_by="child")
    validate("runtime-json", session)
    assert session["child_id"] == engine.child_id


def test_start_session_records_honest_initiation(engine):
    session = engine.start_session(initiated_by="child")
    events = [e for e in engine.store.events_for(engine.child_id)
              if e.event_type == "session.started"]
    last = events[-1]
    assert last.payload["initiated_by"] == "child"
    assert last.payload["session_id"] == session["session_id"]


def test_start_session_uses_active_chapter(engine):
    arc = engine.manager.active
    if arc is None:
        pytest.skip("no active mission at end of timeline")
    chapter = next(c for c in arc["chapters"] if c["status"] == "active")
    session = engine.start_session()
    assert session["chapter_id"] == chapter["chapter_id"]
    assert session["arc_id"] == arc["arc_id"]


def test_interaction_and_doudou_request_events(engine):
    session = engine.start_session(initiated_by="child")
    engine.record_interaction(session["session_id"], "choice",
                              {"choice_id": "opt_mine"})
    engine.request_doudou()
    types = [e.event_type for e in engine.store.events_for(engine.child_id)]
    assert "session.interaction" in types
    assert "child.requested_doudou" in types


def test_voluntary_return_metric_reflects_real_session(engine):
    from runtime.metrics import relationship_metrics
    events = [vars(e) for e in engine.store.events_for(engine.child_id)]
    m = relationship_metrics(events)
    assert m["voluntary_returns"] >= 1
    assert m["child_initiated"] >= 1


def test_bad_initiated_by_rejected(engine):
    with pytest.raises(ValueError):
        engine.start_session(initiated_by="nobody")


def test_session_api_endpoints():
    from fastapi.testclient import TestClient

    from demo.web import app, sessions
    client = TestClient(app)
    with client:
        resp = client.post("/api/v1/session/start",
                           data={"child": "vc_curious", "initiated_by": "child"})
        assert resp.status_code == 200
        session = resp.json()
        validate("runtime-json", session)
        sid = session["session_id"]
        assert sid in sessions
        resp = client.post("/api/v1/session/interaction",
                           data={"session_id": sid, "node_type": "choice",
                                 "data": '{"choice_id": "opt_mine"}'})
        assert resp.json() == {"ok": True}
        resp = client.post("/api/v1/doudou/request", data={"child": "vc_curious"})
        assert resp.json() == {"ok": True}
        resp = client.get("/player", params={"child": "vc_curious",
                                             "session_id": sid})
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
