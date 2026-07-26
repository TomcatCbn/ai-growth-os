"""Review-6 tests: atomic callback idempotency, preview isolation,
point-in-time slicing."""

from __future__ import annotations

import threading
from datetime import date

import pytest

from runtime.contracts import ContractViolation
from runtime.events.store import EventStore
from runtime.metrics import relationship_metrics
from runtime.state.callbacks import apply_callback
from runtime.state.relationship_events import slice_to
from runtime.twin.partner import trust_from_events


def _callback_session(store: EventStore, source: str = "child_mode") -> str:
    store.append("session.started", "c1", {
        "session_id": f"s_{source}", "date": "2026-07-26",
        "launch_source": source, "arc_id": "a1"})
    return f"s_{source}"


def test_concurrent_shown_writes_exactly_once(tmp_path):
    store = EventStore(tmp_path / "race.db")
    sid = _callback_session(store)

    def fire():
        apply_callback(store, child_id="c1", session_id=sid, moment="m",
                       transition="shown", launch_source="child_mode",
                       date="2026-07-26")

    threads = [threading.Thread(target=fire) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    offered = [e for e in store.events_for("c1")
               if e.event_type == "partner.callback_offered"]
    assert len(offered) == 1


def test_concurrent_answer_writes_first_answer_only(tmp_path):
    store = EventStore(tmp_path / "race2.db")
    sid = _callback_session(store)
    apply_callback(store, child_id="c1", session_id=sid, moment="m",
                   transition="shown", launch_source="child_mode",
                   date="2026-07-26")

    def fire(resp):
        apply_callback(store, child_id="c1", session_id=sid, moment="m",
                       transition="answered", launch_source="child_mode",
                       date="2026-07-26", response=resp)

    threads = [threading.Thread(target=fire, args=(r,))
               for r in ("recognized", "ignored") * 5]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    answered = [e for e in store.events_for("c1")
                if e.event_type == "partner.callback_recognized"]
    assert len(answered) == 1


def test_out_of_order_still_hard_fails():
    store = EventStore()
    sid = _callback_session(store)
    with pytest.raises(ContractViolation):
        apply_callback(store, child_id="c1", session_id=sid, moment="m",
                       transition="answered", launch_source="child_mode",
                       date="2026-07-26")


def test_preview_callbacks_never_touch_metrics_or_trust():
    store = EventStore()
    sid = _callback_session(store, source="parent_preview")
    apply_callback(store, child_id="c1", session_id=sid, moment="m",
                   transition="shown", launch_source="parent_preview",
                   date="2026-07-26")
    apply_callback(store, child_id="c1", session_id=sid, moment="m",
                   transition="answered", launch_source="parent_preview",
                   date="2026-07-26", response="recognized")
    store.append("child.requested_doudou", "c1", {
        "date": "2026-07-26", "launch_source": "parent_preview"})
    events = [vars(e) for e in store.events_for("c1")]
    m = relationship_metrics(events, as_of=date(2026, 7, 26))
    assert m["callbacks_offered"] == 0
    assert m["callbacks_recognized"] == 0
    assert m["callback_recognition_rate"] is None
    assert m["child_initiated"] == 0
    assert trust_from_events(events) == 0.0


def test_as_of_slices_everything_not_just_windows():
    store = EventStore()
    store.append("session.started", "c1", {
        "session_id": "s1", "date": "2026-07-20", "launch_source": "child_mode",
        "arc_id": "a1"})
    store.append("session.started", "c1", {
        "session_id": "s2", "date": "2026-07-25", "launch_source": "child_mode",
        "arc_id": "a1"})
    store.append("partner.callback_offered", "c1", {
        "moment": "m", "session_id": "s2", "launch_source": "child_mode",
        "date": "2026-07-25"})
    events = [vars(e) for e in store.events_for("c1")]
    # report as of 07-21: the 07-25 session + callback must not exist yet
    m = relationship_metrics(events, as_of=date(2026, 7, 21))
    assert m["session_days"] == 1
    assert m["voluntary_returns"] == 0
    assert m["callbacks_offered"] == 0
    assert m["adventure_continuation"] == 0
    m_later = relationship_metrics(events, as_of=date(2026, 7, 26))
    assert m_later["session_days"] == 2
    assert m_later["callbacks_offered"] == 1


def test_slice_to_uses_semantic_date():
    events = [
        {"event_type": "x", "payload": {"date": "2026-07-20"},
         "created_at": "2026-07-26T00:00:00+00:00"},
        {"event_type": "y", "payload": {},
         "created_at": "2026-07-19T00:00:00+00:00"},
        {"event_type": "z", "payload": {"date": "2026-07-27"},
         "created_at": "2026-07-26T00:00:00+00:00"},
    ]
    sliced = slice_to(events, date(2026, 7, 21))
    assert [e["event_type"] for e in sliced] == ["x", "y"]


def test_recognition_rate_capped_by_dedupe():
    store = EventStore()
    sid = _callback_session(store)
    # simulate a duplicated write (pre-fix data): same fact twice
    for _ in range(2):
        store.append("partner.callback_offered", "c1", {
            "moment": "m", "session_id": sid, "launch_source": "child_mode",
            "date": "2026-07-26"})
        store.append("partner.callback_recognized", "c1", {
            "moment": "m", "session_id": sid, "launch_source": "child_mode",
            "response": "recognized", "date": "2026-07-26"})
    events = [vars(e) for e in store.events_for("c1")]
    m = relationship_metrics(events, as_of=date(2026, 7, 26))
    assert m["callbacks_offered"] == 1
    assert m["callbacks_recognized"] == 1
    assert m["callback_recognition_rate"] == 1.0  # never above 1
