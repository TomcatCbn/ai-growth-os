"""Twin projection (ADR-013) — events + derived views → Child Digital Twin.

A pure projection: deterministic, replayable, contract-validated on every
build. Raw views READ the Reducer/derived state; insight entries always cite
supporting events. Numeric truth stays with the Reducer (ADR-004).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..contracts import validate
from ..state.memory import growth_memory_from_events
from ..state.trends import capability_trends


def project_twin(
    *,
    child: dict,
    events: list[dict],
    state: dict,
    capabilities: dict[str, dict],
) -> dict:
    """Build the twin contract object.

    child: profile dict (name/age/stage). state: growth state (interests +
    raw pockets). capabilities: derived capability view (ADR-004).
    """
    now = datetime.now(UTC).isoformat()
    trends = capability_trends(events)

    twin: dict[str, Any] = {
        "child_id": child["child_id"],
        "generated_at": now,
        "identity": {
            "name": child["name"],
            "age": child["age"],
            "stage": child["stage"],
        },
        "interests": [
            {"name": name, "score": round(float(w), 4), "confidence": 0.5}
            for name, w in sorted(state.get("interests", {}).items(),
                                  key=lambda kv: -kv[1])
        ],
        "capabilities": {
            cap: {
                "score": rec["score"],
                "trend": trends.get(cap, {}).get("direction", "steady"),
                "confidence": rec["confidence"],
                "supporting_event_ids": trends.get(cap, {}).get("evidence_refs", []),
            }
            for cap, rec in capabilities.items()
        },
    }

    # Relationship summary (deep partner state arrives with its own
    # projection; trust is a simple deterministic function of shared arcs).
    closed = growth_memory_from_events(events)["closed_arcs"]
    confirmed = sum(1 for a in closed if a["verdict"] == "confirmed")
    twin["relationship"] = {
        "partner_id": "doudou_rabbit",
        "trust_level": round(min(1.0, 0.1 * len(closed) + 0.1 * confirmed), 4),
        "story_progress": f"一起经历了{len(closed)}段冒险" if closed else "故事刚开始",
    }

    validate("child-twin", twin)
    return twin
