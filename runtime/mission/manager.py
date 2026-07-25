"""Mission Manager — owns the present (ADR-006, ADR-011).

Exactly one active mission per child. Lifecycle transitions only here:
activate / advance chapter / close / detect stall. Never writes growth goals
(Planner) and never mutates ChildState (Reducer).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..contracts import validate

STALL_DAYS = 3

_VERDICT = {
    "completed": "confirmed",
    "partial": "inconclusive",
    "not_completed": "refuted",
}


class MissionManager:
    def __init__(self):
        self.active: dict | None = None
        self.activated_at: str | None = None

    def activate(self, arc: dict) -> dict:
        if self.active is not None:
            raise RuntimeError(f"mission {self.active['arc_id']} still active — close it first")
        arc["arc_id"] = arc.get("arc_id") or f"arc_{uuid.uuid4().hex[:10]}"
        arc["status"] = "active"
        arc.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        arc["chapters"][0]["status"] = "active"
        validate("mission-arc", arc)
        self.active = arc
        self.activated_at = datetime.now(timezone.utc).isoformat()
        return arc

    def close(self, checkin_status: str) -> dict:
        """Close the active mission from a check-in; returns the closed arc
        with hypothesis_verdict set (meta-evidence, ADR-007 §1)."""
        if self.active is None:
            raise RuntimeError("no active mission to close")
        arc = self.active
        arc["status"] = "completed" if checkin_status == "completed" else "abandoned"
        arc["hypothesis_verdict"] = _VERDICT[checkin_status]
        arc["closed_at"] = datetime.now(timezone.utc).isoformat()
        self.active = None
        return arc

    def is_stalled(self, now: datetime | None = None) -> bool:
        if self.active is None or self.activated_at is None:
            return False
        now = now or datetime.now(timezone.utc)
        activated = datetime.fromisoformat(self.activated_at)
        return (now - activated).days >= STALL_DAYS
