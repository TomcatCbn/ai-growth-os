"""Event Store — the only system of record (ADR-002, ADR-012).

Three tables with different lifetimes:
- events: append-only facts, permanent. PII-redacted BEFORE insert (Layer 1).
- decision_trace: every LLM judgment (input snapshot, output, rationale).
- snapshots: runtime-state checkpoints; rebuildable from events.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    child_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decision_trace (
    trace_id TEXT PRIMARY KEY,
    component TEXT NOT NULL,
    child_id TEXT,
    input_snapshot TEXT NOT NULL,
    output TEXT NOT NULL,
    rationale TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    child_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    last_event_seq INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    event_id: str
    event_type: str
    child_id: str
    payload: dict[str, Any]
    created_at: str


class EventStore:
    def __init__(self, path: str | Path = ":memory:"):
        # check_same_thread=False: web servers (FastAPI threadpool) call from
        # worker threads; a lock serializes writes instead.
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.executescript(SCHEMA)

    def append(self, event_type: str, child_id: str, payload: dict[str, Any]) -> Event:
        """Append an immutable fact. Caller MUST have run Input Guard first."""
        ev = Event(
            event_id=f"ev_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            child_id=child_id,
            payload=payload,
            created_at=_now(),
        )
        with self._lock:
            self._db.execute(
                "INSERT INTO events (event_id, event_type, child_id, payload, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (ev.event_id, ev.event_type, ev.child_id, json.dumps(ev.payload), ev.created_at),
            )
            self._db.commit()
        return ev

    def trace(
        self,
        component: str,
        input_snapshot: dict[str, Any],
        output: dict[str, Any],
        *,
        child_id: str | None = None,
        rationale: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> str:
        trace_id = f"tr_{uuid.uuid4().hex[:12]}"
        with self._lock:
            self._db.execute(
                "INSERT INTO decision_trace (trace_id, component, child_id, input_snapshot,"
                " output, rationale, model, input_tokens, output_tokens, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    trace_id, component, child_id, json.dumps(input_snapshot),
                    json.dumps(output), rationale, model, input_tokens, output_tokens, _now(),
                ),
            )
            self._db.commit()
        return trace_id

    def events_for(self, child_id: str) -> list[Event]:
        rows = self._db.execute(
            "SELECT event_id, event_type, child_id, payload, created_at"
            " FROM events WHERE child_id = ? ORDER BY seq",
            (child_id,),
        ).fetchall()
        return [
            Event(r[0], r[1], r[2], json.loads(r[3]), r[4]) for r in rows
        ]

    def save_snapshot(self, child_id: str, state: dict[str, Any], last_event_seq: int) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO snapshots (child_id, state, last_event_seq, created_at)"
                " VALUES (?, ?, ?, ?)"
                " ON CONFLICT(child_id) DO UPDATE SET state=excluded.state,"
                " last_event_seq=excluded.last_event_seq, created_at=excluded.created_at",
                (child_id, json.dumps(state), last_event_seq, _now()),
            )
            self._db.commit()
