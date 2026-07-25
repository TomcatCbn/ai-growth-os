"""Character Bible + Prompt OS tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from runtime.contracts import validate
from runtime.llm.prompts import (
    DOUDOU_PERSONA,
    EXTRACTOR,
    PLANNER,
    load_prompt,
)

BIBLE = Path(__file__).resolve().parent.parent / "content" / "doudou-bible.yaml"


def test_character_bible_satisfies_contract():
    bible = yaml.safe_load(BIBLE.read_text())
    validate("character-bible", bible)
    assert bible["character_id"] == "doudou_rabbit"


def test_bible_has_binding_forbidden_behavior():
    bible = yaml.safe_load(BIBLE.read_text())
    assert len(bible["forbidden_behavior"]) >= 5
    assert any("批评" in b for b in bible["forbidden_behavior"])
    assert any("比较" in b for b in bible["forbidden_behavior"])


def test_prompt_versions_load():
    for version in (PLANNER, EXTRACTOR, DOUDOU_PERSONA):
        text = load_prompt(version)
        assert len(text) > 50


def test_unknown_prompt_version_fails_loudly():
    import pytest
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_v99")


def test_planner_uses_prompt_os():
        from runtime.planner.planner import PLANNER_PROMPT_VERSION, SYSTEM
        assert SYSTEM == load_prompt(PLANNER_PROMPT_VERSION)


def test_extractor_uses_prompt_os():
    from runtime.evidence.extractor import EXTRACTOR_PROMPT_VERSION, SYSTEM
    assert SYSTEM == load_prompt(EXTRACTOR_PROMPT_VERSION)
