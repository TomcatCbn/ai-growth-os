"""i18n loader (ADR-005). Canonical knowledge stays English; this layer
overrides display fields per locale without touching upstream data."""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT = Path(__file__).resolve().parent.parent / "i18n" / "zh-CN.yaml"


class I18n:
    def __init__(self, path: str | Path = DEFAULT):
        doc = yaml.safe_load(Path(path).read_text())
        self.locale = doc["locale"]
        self._caps = doc.get("capabilities", {})
        self._topics = doc.get("topics", {})

    def capability_name(self, cap_id: str) -> str:
        return self._caps.get(cap_id, {}).get("name", cap_id)

    def topic_name(self, topic_id: str, fallback: str) -> str:
        return self._topics.get(topic_id, {}).get("name", fallback)

    def topic_evidence_zh(self, topic_id: str, fallback: list[str]) -> list[str]:
        """Observation checklist text. Falls back to canonical English when
        the human-polished zh is not yet available (ADR-005 §4)."""
        return self._topics.get(topic_id, {}).get("evidence", fallback)

    def has_topic_zh(self, topic_id: str) -> bool:
        """False means parent-facing text for this topic falls back to
        English — a coverage gap that must be visible, never silent."""
        return topic_id in self._topics
