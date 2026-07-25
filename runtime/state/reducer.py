"""Reducer — the ONLY writer of growth state (ADR-002 §4, ADR-011).

Pure, deterministic, no LLM. Evidence → Reducer → State.

Update rule (ADR-002): EMA with confidence- and evidence-strength-scaled
step, per-update delta cap, append-only replay.
"""

from __future__ import annotations

ALPHA = 0.4  # base learning rate
MAX_DELTA = 0.2  # single-evidence movement cap
DIRECT_CAPABILITY_STRENGTH_CAP = 0.5  # soft-trait direct channel discount (ADR-004 §4)
REPEAT_WINDOW_SECONDS = 6 * 3600  # same-source re-submission decay window
REPEAT_DECAY = 0.5


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def ema_update(
    old: float,
    signal: float,
    *,
    confidence: float,
    evidence_strength: float,
    direct_channel: bool = False,
) -> float:
    """One evidence item → new mastery/level. All movement is explainable:
    delta = α × confidence × evidence_strength × (signal − old), capped."""
    strength = min(evidence_strength, DIRECT_CAPABILITY_STRENGTH_CAP) if direct_channel else evidence_strength
    delta = ALPHA * confidence * strength * (signal - old)
    delta = max(-MAX_DELTA, min(MAX_DELTA, delta))
    return clamp01(old + delta)


def confidence_for_count(n: int) -> float:
    """Confidence grows with evidence count: 1 obs → 0.3, ~5 obs → 0.7, ≥10 → 0.9."""
    return clamp01(0.2 + 0.07 * n)


def reduce_events(events: list[dict]) -> dict:
    """Replay an event stream into child state (topic_mastery + capability_direct).

    Skeleton: expects events of type 'evidence.signals_extracted' with payload
    {'signals': [...]} matching schemas/evidence.schema.json. Returns the two
    raw pockets of ADR-004 — derived capability views are computed elsewhere.
    """
    topic_mastery: dict[str, dict] = {}
    capability_direct: dict[str, dict] = {}

    for ev in events:
        if ev.get("event_type") != "evidence.signals_extracted":
            continue
        for sig in ev["payload"].get("signals", []):
            pocket = topic_mastery if sig["target_type"] == "topic" else capability_direct
            rec = pocket.setdefault(
                sig["target_id"],
                {"mastery" if sig["target_type"] == "topic" else "level": 0.3,
                 "confidence": 0.0, "evidence_count": 0},
            )
            key = "mastery" if sig["target_type"] == "topic" else "level"
            rec[key] = ema_update(
                rec[key],
                sig["signal_strength"],
                confidence=sig["confidence"],
                evidence_strength=sig.get("evidence_strength", 1.0),
                direct_channel=(sig["target_type"] == "capability"),
            )
            rec["evidence_count"] += 1
            rec["confidence"] = confidence_for_count(rec["evidence_count"])

    return {"topic_mastery": topic_mastery, "capability_direct": capability_direct}
