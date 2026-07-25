"""Adventure template + pace guardrail tests."""

from __future__ import annotations

from demo.arc import (
    load_adventure_templates,
    load_patterns,
    pace_adjustment,
    select_pattern,
    select_template,
)
from runtime.contracts import validate

PATTERNS = load_patterns()
TEMPLATES = load_adventure_templates()


def test_library_has_ten_mvp_templates():
    assert len(TEMPLATES) == 10
    by_pattern = {}
    for t in TEMPLATES:
        by_pattern.setdefault(t["pattern_id"], []).append(t)
    assert len(by_pattern["discovery"]) == 3
    assert len(by_pattern["build"]) == 2
    assert len(by_pattern["help"]) == 2
    assert len(by_pattern["story_creation"]) == 1
    assert len(by_pattern["challenge"]) == 2


def test_templates_validate_and_bind_known_patterns():
    pattern_ids = {p["pattern_id"] for p in PATTERNS}
    for t in TEMPLATES:
        validate("adventure-template", t)
        assert t["pattern_id"] in pattern_ids
        assert len(t["structure"]) >= 2


def _closed(verdicts: list[str]) -> list[dict]:
    events = []
    for i, v in enumerate(verdicts):
        events.append({"event_type": "mission.activated",
                       "payload": {"arc_id": f"a{i}", "topic": "mt_x"}})
        events.append({"event_type": "mission.closed", "event_id": f"ev_c{i}",
                       "payload": {"arc_id": f"a{i}", "verdict": v}})
    return events


def test_pace_ease_after_consecutive_failures():
    assert pace_adjustment(_closed(["refuted", "refuted"])) == "ease"
    assert pace_adjustment(_closed(["confirmed", "refuted"])) == "steady"
    assert pace_adjustment(_closed(["confirmed", "confirmed"])) == "push"
    assert pace_adjustment(_closed(["confirmed"])) == "steady"


def test_ease_prefers_gentler_pattern():
    events = _closed(["refuted", "refuted"])
    easy = select_pattern(PATTERNS, [], events, pace="ease")
    hard = select_pattern(PATTERNS, [], [], pace="push")
    easy_max = max(c["difficulty"] for c in easy["chapter_skeleton"])
    hard_max = max(c["difficulty"] for c in hard["chapter_skeleton"])
    assert easy_max <= hard_max


def test_select_template_prefers_unused():
    events = [
        {"event_type": "mission.activated",
         "payload": {"arc_id": "a1", "template_id": "find_secret"}},
    ]
    picked = select_template(TEMPLATES, "discovery", events)
    assert picked["pattern_id"] == "discovery"
    assert picked["template_id"] != "find_secret"
