"""Knowledge import pipeline (ADR-001, ADR-005).

Reads the os-taxonomy submodule (upstream immutable), filters the age band,
and emits a versioned growth-artifact. Our additive files (capability
taxonomy, mapping, i18n) merge at later pipeline stages — never by editing
upstream.

Usage: python -m knowledge.import_pipeline --source ../os-taxonomy --out knowledge/artifact
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ARTIFACT_VERSION = "0.1"
MVP_AGE_BAND = (4, 6)


def filter_age_band(topics: list[dict], band: tuple[int, int]) -> list[dict]:
    lo, hi = band
    return [t for t in topics if t["ageRangeStart"] <= hi and t["ageRangeEnd"] >= lo]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="path to os-taxonomy repo (submodule)")
    ap.add_argument("--out", required=True, help="artifact output dir")
    args = ap.parse_args()

    src = Path(args.source)
    topics = json.loads((src / "data/topics.json").read_text())["topics"]
    deps = json.loads((src / "data/dependencies.json").read_text())["dependencies"]

    kept = filter_age_band(topics, MVP_AGE_BAND)
    kept_ids = {t["id"] for t in kept}
    kept_deps = [d for d in deps if d["topicId"] in kept_ids and d["prerequisiteId"] in kept_ids]

    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "upstream": {"name": "Marble Skill Taxonomy", "version": "v1",
                      "license": "ODbL-1.0 + CC-BY-SA-4.0",
                      "attribution": "Marble Skill Taxonomy (v1) · © Generative Spark, Inc. (Marble) · https://withmarble.com"},
        "age_band": list(MVP_AGE_BAND),
        "topics": kept,
        "dependencies": kept_deps,
    }
    blob = json.dumps(artifact, ensure_ascii=False, indent=2)
    artifact["sha256"] = hashlib.sha256(blob.encode()).hexdigest()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"growth-artifact-{ARTIFACT_VERSION}.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2)
    )
    print(f"topics: {len(kept)}, dependencies: {len(kept_deps)} → {out}")


if __name__ == "__main__":
    main()
