"""Evidence extraction (ADR-002): free-text observation → typed signals.

Contract: every signal carries a verbatim quote (spot-checkable).
Pure chit-chat MUST extract to an empty signals list — false-positive
discipline is tested by the golden set (evaluation/).
"""

from __future__ import annotations

import json
from typing import Any

from ..contracts import validate_signals
from ..llm.base import LLMRequest
from ..llm.prompts import EXTRACTOR as EXTRACTOR_PROMPT_VERSION
from ..llm.prompts import load_prompt
from ..trace.trace import TrackedProvider

SYSTEM = load_prompt(EXTRACTOR_PROMPT_VERSION)

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["signals"],
    "properties": {
        "signals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["target_type", "target_id", "signal_strength", "confidence", "quote"],
                "properties": {
                    "target_type": {"type": "string", "enum": ["topic", "capability"]},
                    "target_id": {"type": "string"},
                    "signal_strength": {"type": "number", "minimum": 0, "maximum": 1},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "quote": {"type": "string"},
                },
            },
        }
    },
}


class EvidenceExtractor:
    def __init__(self, llm: TrackedProvider):
        self._llm = llm

    def extract(
        self, *, child_id: str, raw_text: str, candidate_targets: list[dict]
    ) -> tuple[list[dict], str]:
        """Returns (signals, trace_id). candidate_targets scopes extraction to
        known topic/capability ids — the extractor may not invent ids."""
        user = json.dumps(
            {"observation": raw_text, "known_targets": candidate_targets},
            ensure_ascii=False,
        )
        resp, trace_id = self._llm.complete(
            LLMRequest(system=SYSTEM, user=user, response_schema=RESPONSE_SCHEMA),
            child_id=child_id,
            context={"prompt_version": EXTRACTOR_PROMPT_VERSION},
        )
        signals = json.loads(resp.content)["signals"]
        validate_signals(signals)
        known = {t["id"] for t in candidate_targets}
        signals = [s for s in signals if s["target_id"] in known]
        for s in signals:
            if s["quote"] not in raw_text:
                s["confidence"] *= 0.5  # unverifiable quote → halve confidence
        return signals, trace_id
