"""Tendency projection (ADR-013 T3) — behavioral styles under observation.

Deterministic v1: capability signals with consistent behavioral meaning map
to open-vocabulary traits. Strong signals support, weak signals contradict.
A tendency is a hypothesis with an evidence chain — never a label. The
LLM-based Insight Agent replaces this heuristic later; the contract stays.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ..contracts import validate

# capability → trait hypothesis (conservative v1 mapping; grows via adjudication)
TRAIT_BY_CAPABILITY = {
    "capability.persistence": "persistent_retry",
    "capability.curiosity": "curious_questioning",
    "capability.storytelling": "story_lover",
    "capability.imaginative_play": "pretend_play_affinity",
    "capability.social_negotiation": "collaborative_style",
}

SUPPORT_THRESHOLD = 0.6   # signal_strength at/above supports the trait
CONTRADICT_THRESHOLD = 0.3  # at/below contradicts
STABLE_MIN_SUPPORTERS = 3


def project_tendencies(events: list[dict]) -> list[dict]:
    """Events → tendency contracts. Deterministic, replayable."""
    hits: dict[str, list[dict]] = {}
    for e in events:
        if e.get("event_type") != "evidence.signals_extracted":
            continue
        for s in e["payload"].get("signals", []):
            trait = TRAIT_BY_CAPABILITY.get(s["target_id"])
            if not trait:
                continue
            strength = s["signal_strength"]
            if strength >= SUPPORT_THRESHOLD:
                direction = "supports"
            elif strength <= CONTRADICT_THRESHOLD:
                direction = "contradicts"
            else:
                continue  # ambiguous evidence is not evidence
            hits.setdefault(trait, []).append({
                "event_id": e.get("event_id", ""),
                "summary": s["quote"],
                "observed_at": e.get("created_at", ""),
                "direction": direction,
            })

    now = datetime.now(UTC).isoformat()
    tendencies = []
    for trait, evidence in sorted(hits.items()):
        supports = sum(1 for x in evidence if x["direction"] == "supports")
        contradicts = len(evidence) - supports
        if supports + contradicts == 0:
            continue
        confidence = round(supports / (supports + contradicts)
                           * min(1.0, 0.2 + 0.1 * supports), 4)
        if contradicts > supports:
            status = "stale"  # history wins
        elif supports >= STABLE_MIN_SUPPORTERS:
            status = "stable"
        else:
            status = "emerging"
        child_id = next(
            (e.get("child_id") for e in events if e.get("child_id")), "")
        tendency = {
            "tendency_id": f"td_{uuid.uuid5(uuid.NAMESPACE_URL, trait + child_id).hex[:10]}",
            "child_id": child_id,
            "trait": trait,
            "evidence": evidence,
            "confidence": confidence,
            "status": status,
            "created_at": evidence[0]["observed_at"] or now,
            "updated_at": evidence[-1]["observed_at"] or now,
        }
        validate("tendency", tendency)
        tendencies.append(tendency)
    return tendencies
