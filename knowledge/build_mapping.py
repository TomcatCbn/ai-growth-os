"""Topic→Capability mapping pipeline (ADR-004 §3).

For each topic in the artifact, produce mapping edges to capabilities with
the four dimensions: relevance / evidence_strength / age_fit /
development_priority (the last defaults from the taxonomy priority table,
overridable per edge).

--live: LLM drafts edges (Claude), code validates (known ids, value ranges,
1-4 edges per topic). A 20% spot-check sample is emitted for human review.
--mock: deterministic subject/domain heuristics — produces a usable baseline
map offline; the real run must beat it on spot-check.

Usage:
  python -m knowledge.build_mapping --mock \
      --artifact knowledge/artifact/growth-artifact-0.1.json \
      --taxonomy world-model/capability-taxonomy.yaml \
      --out world-model/topic-capability-map.yaml
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import yaml

# Deterministic subject/domain → capability heuristics (mock baseline).
SUBJECT_MAP = {
    "Mathematics": [("capability.numeracy_sense", 0.9), ("capability.pattern_recognition", 0.6)],
    "Science": [("capability.observation", 0.9), ("capability.causal_reasoning", 0.6)],
    "English": [("capability.vocabulary_use", 0.6), ("capability.listening_comprehension", 0.6)],
    "History": [("capability.causal_reasoning", 0.6), ("capability.storytelling", 0.6)],
    "Personal & Social Development": [("capability.emotion_regulation", 0.9),
                                       ("capability.social_negotiation", 0.6)],
    "Life Skills": [("capability.planning", 0.6), ("capability.impulse_control", 0.6)],
    "Computing": [("capability.pattern_recognition", 0.6), ("capability.planning", 0.6)],
    "Learning to Learn": [("capability.persistence", 0.9), ("capability.focused_attention", 0.6)],
}
DOMAIN_HINTS = {
    "grammar": ("capability.vocabulary_use", 0.9),
    "reading": ("capability.listening_comprehension", 0.9),
    "writing": ("capability.storytelling", 0.9),
    "speaking": ("capability.dialogue_turn_taking", 0.9),
    "shape": ("capability.spatial_reasoning", 0.9),
    "measurement": ("capability.numeracy_sense", 0.9),
    "counting": ("capability.numeracy_sense", 0.9),
    "pattern": ("capability.pattern_recognition", 0.9),
}

AGE_CENTER = {4: 4.5, 5: 5.0, 6: 5.5}  # topic age fit reference


def mock_edges(topic: dict) -> list[dict]:
    edges = dict(SUBJECT_MAP.get(topic["subject"], []))
    domain_l = (topic.get("domain") or "").lower()
    for hint, (cap, w) in DOMAIN_HINTS.items():
        if hint in domain_l:
            edges[cap] = w
    if not edges:
        edges[("capability.observation", 0.3)] = 0.3
    center = (topic["ageRangeStart"] + topic["ageRangeEnd"]) / 2
    age_fit = 0.9 if 4 <= center <= 6 else 0.6
    return [
        {"capability": cap, "relevance": w, "evidence_strength": 0.6, "age_fit": age_fit}
        for cap, w in edges.items()
    ]


def validate_edges(edges: list[dict], known_caps: set[str]) -> list[dict]:
    out = []
    for e in edges:
        if e["capability"] not in known_caps:
            continue
        for dim in ("relevance", "evidence_strength", "age_fit"):
            e[dim] = max(0.0, min(1.0, float(e[dim])))
        out.append(e)
    return out[:4]  # at most 4 capability edges per topic


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    artifact = json.loads(Path(args.artifact).read_text())
    taxonomy = yaml.safe_load(Path(args.taxonomy).read_text())
    caps = {
        c["id"]: c
        for d in taxonomy["domains"].values()
        for c in d["capabilities"]
    }

    if args.live:
        raise SystemExit("live LLM mapping requires ANTHROPIC_API_KEY; use --mock offline")
    if not args.mock:
        raise SystemExit("choose --mock or --live")

    mapping = {}
    for t in artifact["topics"]:
        edges = validate_edges(mock_edges(t), set(caps))
        # development_priority defaults from the capability×age table (ADR-004 §3)
        for e in edges:
            pri = caps[e["capability"]]["priority"]
            e["development_priority"] = {band: float(p) for band, p in pri.items()}
        mapping[t["id"]] = edges

    doc = {
        "version": "0.1-mock",
        "generator": "build_mapping --mock (deterministic heuristics; replace with --live + spot-check)",
        "edges": mapping,
    }
    out = Path(args.out)
    out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))

    # 20% spot-check sample for human review (ADR-004: LLM-initial + human check)
    rng = random.Random(42)
    sample_ids = rng.sample(sorted(mapping), k=max(1, len(mapping) // 5))
    sample = {tid: mapping[tid] for tid in sample_ids}
    spot = out.with_name(out.stem + ".spotcheck.yaml")
    spot.write_text(yaml.safe_dump(sample, allow_unicode=True, sort_keys=False))
    print(f"topics mapped: {len(mapping)} → {out}")
    print(f"spot-check sample ({len(sample)}): {spot}")


if __name__ == "__main__":
    main()
