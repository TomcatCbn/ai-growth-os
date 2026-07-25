"""Derived capability view (ADR-004 §3-4) — never stored, always derived.

One aggregation formula, defined once, read by both the Planner and parent
reports:

    topic_derived(c) = Σ(mastery[t] × relevance × age_fit) / Σ(relevance × age_fit)
    fused(c)         = (n_topic × topic_derived + n_direct × direct) / (n_topic + n_direct)

The direct channel is secondary (ADR-004 §4): it only moves the fused score
in proportion to its evidence count, and its per-evidence strength was
already capped at 0.5 by the Reducer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_MAP = Path(__file__).resolve().parent.parent.parent / "world-model" / "topic-capability-map.yaml"


class UnadjudicatedAssetError(Exception):
    pass


def age_band(age: float) -> str:
    return str(min(6, max(4, int(age))))


def load_capability_map(
    path: str | Path = DEFAULT_MAP, *, allow_mock: bool = False
) -> dict[str, list[dict[str, Any]]]:
    """Load the topic→capability map. Mock/heuristic maps are domain-model
    risks, not tech debt (ADR-004 §2-3): they are rejected unless the caller
    explicitly opts in (demo/baseline use only)."""
    doc = yaml.safe_load(Path(path).read_text())
    version = str(doc.get("version", ""))
    if "mock" in version and not allow_mock:
        raise UnadjudicatedAssetError(
            f"{path} is version '{version}' — heuristic mock, not expert-adjudicated. "
            "Formal runtime must use a spot-checked map (--live + spot-check); "
            "pass allow_mock=True only for demo/baseline runs."
        )
    return doc["edges"]


def topic_capabilities(topic_id: str, cap_map: dict[str, list[dict]]) -> list[str]:
    return [e["capability"] for e in cap_map.get(topic_id, [])]


def derive_capabilities(
    topic_mastery: dict[str, dict],
    capability_direct: dict[str, dict],
    cap_map: dict[str, list[dict]],
    *,
    age: float = 5,
) -> dict[str, dict[str, Any]]:
    """Fuse topic-derived evidence (primary) with direct evidence (secondary).

    Returns cap_id -> {score, confidence, topic_derived, direct,
    topic_evidence_count, direct_evidence_count} — every number traceable.
    """
    weighted_sum: dict[str, float] = {}
    weight_total: dict[str, float] = {}
    topic_counts: dict[str, int] = {}

    for tid, rec in topic_mastery.items():
        for edge in cap_map.get(tid, []):
            cap = edge["capability"]
            w = edge["relevance"] * edge.get("age_fit", 1.0)
            weighted_sum[cap] = weighted_sum.get(cap, 0.0) + rec["mastery"] * w
            weight_total[cap] = weight_total.get(cap, 0.0) + w
            topic_counts[cap] = topic_counts.get(cap, 0) + rec["evidence_count"]

    view: dict[str, dict[str, Any]] = {}
    for cap in set(weighted_sum) | set(capability_direct):
        td = weighted_sum[cap] / weight_total[cap] if weight_total.get(cap) else None
        direct = capability_direct.get(cap)
        n_topic = topic_counts.get(cap, 0)
        n_direct = direct["evidence_count"] if direct else 0
        if td is None:
            score = direct["level"]
        elif direct is None:
            score = td
        else:
            score = (n_topic * td + n_direct * direct["level"]) / (n_topic + n_direct)
        view[cap] = {
            "score": round(score, 4),
            "topic_derived": round(td, 4) if td is not None else None,
            "direct": round(direct["level"], 4) if direct else None,
            "topic_evidence_count": n_topic,
            "direct_evidence_count": n_direct,
            "confidence": round(min(1.0, 0.2 + 0.07 * (n_topic + n_direct)), 4),
        }
    return view


def development_priorities(
    cap_map: dict[str, list[dict]], topic_id: str, *, age: float = 5
) -> dict[str, float]:
    """capability_id -> development_priority at the child's age band, for the
    Planner's frontier ranking (ADR-003/004 §3)."""
    band = age_band(age)
    return {
        e["capability"]: e.get("development_priority", {}).get(band, 0.5)
        for e in cap_map.get(topic_id, [])
    }
