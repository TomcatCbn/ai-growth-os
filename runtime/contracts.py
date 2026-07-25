"""Contract module — schemas are the source of truth (Schema Contract First).

Every object crossing a component boundary — Planner output, MissionArc,
evidence signals, ParentInsight — MUST validate against schemas/ before it
is stored, replayed, or shown. No component hand-rolls its own checks.

Hard failure on violation: a contract breach is a bug, never a warning.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


class ContractViolation(Exception):
    pass


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft7Validator:
    path = SCHEMA_DIR / f"{name}.schema.json"
    schema = json.loads(path.read_text())
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


def validate(name: str, instance: dict[str, Any]) -> dict[str, Any]:
    """Validate instance against schemas/<name>.schema.json. Returns the
    instance unchanged; raises ContractViolation on the first breach."""
    errors = sorted(_validator(name).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        e = errors[0]
        loc = ".".join(str(p) for p in e.absolute_path) or "(root)"
        raise ContractViolation(f"{name} contract violated at {loc}: {e.message}")
    return instance


def validate_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate extracted signals against the evidence contract's signal
    item schema (schemas/evidence.schema.json → properties.signals.items)."""
    item_schema = _validator("evidence").schema["properties"]["signals"]["items"]
    validator = Draft7Validator(item_schema)
    for i, sig in enumerate(signals):
        errors = sorted(validator.iter_errors(sig), key=lambda e: list(e.path))
        if errors:
            e = errors[0]
            loc = ".".join(str(p) for p in e.absolute_path) or "(root)"
            raise ContractViolation(f"evidence signal[{i}] violated at {loc}: {e.message}")
    return signals
