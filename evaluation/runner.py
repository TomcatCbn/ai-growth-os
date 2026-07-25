"""Evaluation runner — first-class module (ADR-010).

Scores evidence extraction against the hand-labeled golden set.
Acceptance gates (final review): precision ≥ 0.8 AND recall ≥ 0.7 —
precision prioritized: missed signals acceptable, spurious ones dangerous.

Modes:
  --mock   offline: the REAL EvidenceExtractor driven by MockLLMProvider
           (keyword baseline). Tests the extraction contract end-to-end;
           the real LLM must beat this baseline.
  --live   real extractor (runtime.evidence.extractor + Claude). Needs
           ANTHROPIC_API_KEY and a knowledge artifact.

Usage:
  python -m evaluation.runner --mock
  python -m evaluation.runner --live --artifact knowledge/artifact/growth-artifact-0.1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

GOLDEN = Path(__file__).parent / "golden-set.yaml"
PRECISION_GATE = 0.8
RECALL_GATE = 0.7


@dataclass
class Scores:
    precision: float
    recall: float
    n_cases: int


def score_extraction(cases: list[dict], extract) -> Scores:
    """extract(raw_text) -> iterable of target_id strings."""
    tp = fp = fn = 0
    for case in cases:
        predicted = set(extract(case["raw_text"]))
        expected = {e["target_id"] for e in case.get("expected_signals", [])}
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return Scores(precision=precision, recall=recall, n_cases=len(cases))


# --- extractors -------------------------------------------------------------

def mock_extractor(cases: list[dict]):
    """Offline baseline: the real EvidenceExtractor contract (candidate-target
    scoping, verbatim-quote check) driven by MockLLMProvider keywords."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from demo.mock_llm import MockLLMProvider
    from runtime.events.store import EventStore
    from runtime.evidence.extractor import EvidenceExtractor
    from runtime.trace.trace import TrackedProvider

    taxonomy = yaml.safe_load(
        (Path(__file__).resolve().parent.parent / "world-model" / "capability-taxonomy.yaml")
        .read_text())
    targets = [
        {"id": c["id"], "name": c["name_zh"]}
        for d in taxonomy["domains"].values() for c in d["capabilities"]
    ]
    llm = TrackedProvider(MockLLMProvider(), EventStore(), component="eval.mock")
    extractor = EvidenceExtractor(llm)

    def extract(raw_text: str) -> list[str]:
        signals, _ = extractor.extract(
            child_id="eval", raw_text=raw_text, candidate_targets=targets)
        return [s["target_id"] for s in signals]

    return extract


def live_extractor(artifact_path: str, child_id: str = "eval"):
    from runtime.events.store import EventStore
    from runtime.evidence.extractor import EvidenceExtractor
    from runtime.llm.claude import ClaudeProvider
    from runtime.trace.trace import TrackedProvider

    artifact = json.loads(Path(artifact_path).read_text())
    targets = [{"id": t["id"], "name": t["name"]} for t in artifact["topics"]]
    # Capability ids come from the (future) capability taxonomy; for now the
    # golden set defines the universe so extraction can target them.
    cases = yaml.safe_load(GOLDEN.read_text())["cases"]
    targets += [{"id": e["target_id"]} for c in cases for e in c.get("expected_signals", [])]

    llm = TrackedProvider(ClaudeProvider(), EventStore(), component="eval.extractor")
    extractor = EvidenceExtractor(llm)

    def extract(raw_text: str) -> list[str]:
        signals, _ = extractor.extract(
            child_id=child_id, raw_text=raw_text, candidate_targets=targets
        )
        return [s["target_id"] for s in signals]

    return extract


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", default=str(GOLDEN))
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--artifact", help="knowledge artifact path (live mode)")
    args = ap.parse_args()

    cases = yaml.safe_load(Path(args.golden).read_text())["cases"]

    if args.live:
        if not args.artifact:
            raise SystemExit("--live requires --artifact")
        extract = live_extractor(args.artifact)
    elif args.mock:
        extract = mock_extractor(cases)
    else:
        raise SystemExit("choose --mock or --live")

    scores = score_extraction(cases, extract)
    print(f"cases={scores.n_cases}  precision={scores.precision:.2f}  recall={scores.recall:.2f}")
    ok = scores.precision >= PRECISION_GATE and scores.recall >= RECALL_GATE
    print(f"gates: precision>={PRECISION_GATE} recall>={RECALL_GATE} → {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
