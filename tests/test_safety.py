"""Safety tests — guards are enforced inside the store, not by caller memory."""

from __future__ import annotations

from runtime.events.store import EventStore
from runtime.safety.guards import InputGuard, OutputGuard


def test_append_screens_nested_pii():
    store = EventStore()
    ev = store.append("evidence.submitted", "c1", {
        "raw_text": "孩子电话13812345678，今天搭积木",
        "nested": {"quotes": ["邮箱 parent@example.com 提到规律"]},
        "items": ["身份证号 110101199001011234"],
    })
    assert "13812345678" not in ev.payload["raw_text"]
    assert "parent@example.com" not in ev.payload["nested"]["quotes"][0]
    assert "110101199001011234" not in ev.payload["items"][0]
    assert "[REDACTED]" in ev.payload["raw_text"]


def test_screening_is_logged_as_safety_event():
    store = EventStore()
    store.append("evidence.submitted", "c1", {"raw_text": "电话13812345678"})
    # Safety Memory is a SEPARATE stream (ADR-008), not the growth record.
    assert "safety.input_screened" not in [e.event_type for e in store.events_for("c1")]
    assert "safety.input_screened" in [
        e.event_type for e in store.safety_events_for("c1")]


def test_clean_payload_leaves_no_safety_event():
    store = EventStore()
    store.append("evidence.submitted", "c1", {"raw_text": "孩子发现了红黄规律"})
    types = [e.event_type for e in store.events_for("c1")]
    assert types == ["evidence.submitted"]
    assert store.safety_events_for("c1") == []


def test_trace_snapshots_are_screened():
    store = EventStore()
    store.trace("test", input_snapshot={"user": "联系13812345678"},
                output={"content": "ok"}, child_id="c1")
    traces = store.decision_traces("c1")
    assert "13812345678" not in str(traces[0]["input_snapshot"])


def test_screen_payload_is_idempotent():
    guard = InputGuard()
    once, flags1 = guard.screen_payload({"t": "电话13812345678"})
    twice, flags2 = guard.screen_payload(once)
    assert once == twice
    assert flags1 == ["pii_redacted"] and flags2 == []


def _arc_with(field: str, value: str) -> dict:
    chapter = {
        "chapter_id": "ch_1", "narration": "n", "real_world_task": "t",
        "return_prompt": "p", "observation_checklist": ["o"],
    }
    if field == "observation_checklist":
        chapter[field] = [value]
    else:
        chapter[field] = value
    return {"growth_hypothesis": {"statement": "s", "key_signal": "k"},
            "chapters": [chapter]}


def test_output_guard_covers_all_arc_fields():
    guard = OutputGuard()
    for field in ("narration", "real_world_task", "return_prompt", "observation_checklist"):
        result = guard.review_arc(_arc_with(field, "包含恐怖内容"))
        assert not result.passed, field
        assert any(f.startswith(field) for f in result.flags)


def test_output_guard_covers_hypothesis():
    guard = OutputGuard()
    arc = _arc_with("narration", "n")
    arc["growth_hypothesis"]["statement"] = "血腥假设"
    assert not guard.review_arc(arc).passed


def test_clean_arc_passes():
    guard = OutputGuard()
    assert guard.review_arc(_arc_with("narration", "豆豆兔发现了规律")).passed
