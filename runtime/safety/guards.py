"""Safety Kernel — the single channel for all data in / content out (ADR-008).

Layer 1 (Input Guard): PII redaction + injection screening BEFORE event log.
Layer 2 (Output Guard): independent review of everything reaching human eyes.
Layer 3 (Interaction): relationship rules — enforced as generation constraints
and config flags (no streaks, no guilt loops, session closing, parent override).

All guard actions are logged to Safety Memory (safety events stream).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Layer 1 — crude PII patterns for the skeleton; replace with a real NER/model pass.
# NOTE: use digit lookarounds, not \b — CJK chars are word chars, so \b never
# fires between hanzi and digits.
_PII_PATTERNS = [
    re.compile(r"(?<!\d)\d{11}(?!\d)"),  # CN phone
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),  # email
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),  # CN ID card
]

_RED_LINE_TERMS = ["杀", "血腥", "自杀", "恐怖"]  # placeholder; real list lives in evaluation red-line set


@dataclass
class GuardResult:
    passed: bool
    text: str
    flags: list[str] = field(default_factory=list)


class InputGuard:
    def screen(self, raw_text: str) -> GuardResult:
        flags = []
        text = raw_text
        for pat in _PII_PATTERNS:
            if pat.search(text):
                text = pat.sub("[REDACTED]", text)
                flags.append("pii_redacted")
        return GuardResult(passed=True, text=text, flags=flags)


class OutputGuard:
    def review(self, content: str, *, audience: str = "child") -> GuardResult:
        """Independent post-generation check. v1: rule-based; v2: dedicated
        review model, tested against the red-line suite."""
        hits = [t for t in _RED_LINE_TERMS if t in content]
        if hits:
            return GuardResult(passed=False, text=content, flags=[f"red_line:{t}" for t in hits])
        return GuardResult(passed=True, text=content)
