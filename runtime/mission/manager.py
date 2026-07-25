"""Mission Manager — owns the present (ADR-006, ADR-011).

Exactly one active mission per child. Lifecycle transitions only here:
activate / advance chapter / close / detect stall. Never writes growth goals
(Planner) and never mutates ChildState (Reducer).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

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
        arc.setdefault("created_at", datetime.now(UTC).isoformat())
        arc["chapters"][0]["status"] = "active"
        validate("mission-arc", arc)
        self.active = arc
        self.activated_at = datetime.now(UTC).isoformat()
        return arc

    def close(self, checkin_status: str) -> dict:
        """Close the active mission from a check-in; returns the closed arc
        with hypothesis_verdict set (meta-evidence, ADR-007 §1)."""
        if self.active is None:
            raise RuntimeError("no active mission to close")
        arc = self.active
        arc["status"] = "completed" if checkin_status == "completed" else "abandoned"
        arc["hypothesis_verdict"] = _VERDICT[checkin_status]
        arc["closed_at"] = datetime.now(UTC).isoformat()
        self.active = None
        return arc

    def advance_chapter(self) -> dict:
        """Mark the active chapter done and activate the next one. Returns the
        newly active chapter. Raises if the arc is already on its last chapter."""
        if self.active is None:
            raise RuntimeError("no active mission to advance")
        chapters = self.active["chapters"]
        current = next(i for i, c in enumerate(chapters) if c["status"] == "active")
        if current == len(chapters) - 1:
            raise RuntimeError("already on the last chapter — close the mission instead")
        chapters[current]["status"] = "done"
        chapters[current + 1]["status"] = "active"
        return chapters[current + 1]

    def is_stalled(self, now: datetime | None = None) -> bool:
        if self.active is None or self.activated_at is None:
            return False
        now = now or datetime.now(UTC)
        activated = datetime.fromisoformat(self.activated_at)
        return (now - activated).days >= STALL_DAYS

    def snapshot(self) -> dict:
        """Runtime-state pocket for snapshots: active mission + chapter progress.
        Separate from Growth Memory (Reducer state) per ADR-011."""
        return {"active": self.active, "activated_at": self.activated_at}

    @classmethod
    def from_events(cls, events: list[dict]) -> MissionManager:
        """Replay mission lifecycle events into runtime state (ADR-002 §5:
        everything is recoverable from the event log).

        Consumes: mission.activated (payload.arc = full arc),
        mission.chapter_advanced, mission.closed. The manager is a pure
        projection — the same events always rebuild the same runtime state."""
        mgr = cls()
        for ev in events:
            etype = ev.get("event_type")
            payload = ev.get("payload", {})
            if etype == "mission.activated":
                mgr.active = dict(payload["arc"])
                mgr.activated_at = payload.get("activated_at") or ev.get("created_at")
            elif etype == "mission.chapter_advanced" and mgr.active is not None:
                chapter_id = payload.get("chapter_id")
                chapters = mgr.active["chapters"]
                for i, ch in enumerate(chapters):
                    if ch["chapter_id"] == chapter_id:
                        ch["status"] = "active"
                        for prev in chapters[:i]:
                            if prev["status"] == "active":
                                prev["status"] = "done"
                        break
            elif etype == "mission.closed" and mgr.active is not None:
                mgr.active["status"] = payload.get("status", "completed")
                mgr.active["hypothesis_verdict"] = payload.get("verdict")
                mgr.active["closed_at"] = ev.get("created_at")
                mgr.active = None
                mgr.activated_at = None
        return mgr
