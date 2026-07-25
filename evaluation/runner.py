"""Evaluation runner — first-class module (ADR-010).

Runs the extraction golden set: precision ≥ 0.8 AND recall ≥ 0.7
(precision prioritized: missed signals acceptable, spurious ones dangerous).
Extend with: red-line suite (Layer 2), frontier legality, planner A/B.

Usage: python -m evaluation.runner --golden evaluation/golden-set.yaml --extractor <impl>
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import yaml


@dataclass
class Scores:
    precision: float
    recall: float
    n_cases: int


def score_extraction(cases: list[dict], extract) -> Scores:
    """extract(raw_text) -> list of signals with target_id. Compares id sets."""
    tp = fp = fn = 0
    for case in cases:
        predicted = {s["target_id"] for s in extract(case["raw_text"])}
        expected = {e["target_id"] for e in case.get("expected_signals", [])}
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return Scores(precision=precision, recall=recall, n_cases=len(cases))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", required=True)
    args = ap.parse_args()
    with open(args.golden) as f:
        cases = yaml.safe_load(f)["cases"]
    # Wire a real extractor (runtime.evidence.extractor) here when running live.
    raise SystemExit(
        f"Loaded {len(cases)} golden cases. Provide an extractor callable to score."
    )


if __name__ == "__main__":
    main()
