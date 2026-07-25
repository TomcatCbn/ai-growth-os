"""Capability trend projection — first-half vs second-half signal movement.

One implementation, read by both the Parent Coach (ADR-009) and the Twin
projection (ADR-013). Direction is always vs. the child's own past.
"""

from __future__ import annotations

from typing import Any

SWING = 0.1  # minimum mean difference to call a trend up/down


def capability_trends(events: list[dict]) -> dict[str, dict[str, Any]]:
    """cap_id -> {direction, evidence_refs}. Direction compares the mean
    signal strength of the latter half of observations vs. the former half."""
    per_cap: dict[str, list[tuple[float, str]]] = {}
    for e in events:
        if e.get("event_type") != "evidence.signals_extracted":
            continue
        for s in e["payload"].get("signals", []):
            if s["target_type"] != "capability":
                continue
            per_cap.setdefault(s["target_id"], []).append(
                (s["signal_strength"], e.get("event_id", "")))
    trends: dict[str, dict[str, Any]] = {}
    for cap, entries in sorted(per_cap.items()):
        strengths = [x[0] for x in entries]
        if len(strengths) >= 2:
            half = max(1, len(strengths) // 2)
            diff = (sum(strengths[-half:]) / half) - (sum(strengths[:half]) / half)
            direction = "up" if diff > SWING else "down" if diff < -SWING else "steady"
        else:
            direction = "steady"
        trends[cap] = {
            "direction": direction,
            "evidence_refs": [eid for _, eid in entries if eid],
        }
    return trends
