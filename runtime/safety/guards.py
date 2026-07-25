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


def _walk_strings(obj, fn):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_walk_strings(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: _walk_strings(v, fn) for k, v in obj.items()}
    return obj


class InputGuard:
    def screen(self, raw_text: str) -> GuardResult:
        flags = []
        text = raw_text
        for pat in _PII_PATTERNS:
            if pat.search(text):
                text = pat.sub("[REDACTED]", text)
                flags.append("pii_redacted")
        return GuardResult(passed=True, text=text, flags=flags)

    def screen_payload(self, payload: dict) -> tuple[dict, list[str]]:
        """Recursively screen every string in an event payload. This is the
        enforcement point — EventStore calls it on every append, so PII
        cannot reach the event log even if a caller forgets to screen."""
        flags: list[str] = []

        def fn(s: str) -> str:
            r = self.screen(s)
            flags.extend(r.flags)
            return r.text

        return _walk_strings(payload, fn), sorted(set(flags))


class OutputGuard:
    # Every arc field that reaches human eyes (child or parent).
    CHAPTER_TEXT_FIELDS = ("narration", "real_world_task", "return_prompt")

    def review(self, content: str, *, audience: str = "child") -> GuardResult:
        """Independent post-generation check. v1: rule-based; v2: dedicated
        review model, tested against the red-line suite."""
        hits = [t for t in _RED_LINE_TERMS if t in content]
        if hits:
            return GuardResult(passed=False, text=content, flags=[f"red_line:{t}" for t in hits])
        return GuardResult(passed=True, text=content)

    def review_arc(self, arc: dict) -> GuardResult:
        """Review ALL human-facing arc content: narration, real-world task,
        return prompt, observation checklist, and the growth hypothesis.
        Narration-only review is a contract breach (ADR-008 Layer 2)."""
        flags: list[str] = []
        hypothesis = arc.get("growth_hypothesis", {})
        for text in (hypothesis.get("statement", ""), hypothesis.get("key_signal", "")):
            r = self.review(text, audience="parent")
            flags.extend(f"growth_hypothesis:{f}" for f in r.flags)
        for ch in arc.get("chapters", []):
            for field_name in self.CHAPTER_TEXT_FIELDS:
                r = self.review(ch.get(field_name, ""), audience="child")
                flags.extend(f"{field_name}:{f}" for f in r.flags)
            for item in ch.get("observation_checklist", []):
                r = self.review(item, audience="parent")
                flags.extend(f"observation_checklist:{f}" for f in r.flags)
        return GuardResult(passed=not flags, text="", flags=flags)
