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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..safety.guards import InputGuard

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
-- Atomic idempotency keys (review6: read-check-append races must not
-- duplicate relationship facts). PRIMARY KEY is the race arbiter.
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idem_key TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
-- Safety Memory (ADR-008): guard actions live in their own stream, separate
-- from content events, so access control can differ.
CREATE TABLE IF NOT EXISTS safety_events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    child_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Event:
    event_id: str
    event_type: str
    child_id: str
    payload: dict[str, Any]
    created_at: str


class EventStore:
    def __init__(self, path: str | Path = ":memory:", input_guard: InputGuard | None = None):
        # check_same_thread=False: web servers (FastAPI threadpool) call from
        # worker threads; a lock serializes writes instead.
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.executescript(SCHEMA)
        # Layer 1 enforcement lives HERE (ADR-008): every append is screened,
        # so PII cannot enter the event log even if a caller forgets.
        self._guard = input_guard or InputGuard()

    def append(self, event_type: str, child_id: str, payload: dict[str, Any],
               event_id: str | None = None) -> Event:
        """Append an immutable fact. Payload is PII-screened inside — the
        Input Guard is not the caller's responsibility."""
        payload, flags = self._guard.screen_payload(payload)
        ev = Event(
            event_id=event_id or f"ev_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            child_id=child_id,
            payload=payload,
            created_at=_now(),
        )
        with self._lock:
            self._insert_event(ev)
            if flags:
                self._insert_safety_event(Event(
                    event_id=f"ev_{uuid.uuid4().hex[:12]}",
                    event_type="safety.input_screened",
                    child_id=child_id,
                    payload={"flags": flags, "screened_event": ev.event_id},
                    created_at=_now(),
                ))
            self._db.commit()
        return ev

    def append_safety(self, event_type: str, child_id: str, payload: dict[str, Any]) -> Event:
        """Safety Memory entry (output rejections, guard actions). Separate
        stream from the growth record (ADR-008). Screened like everything
        else — safety events may carry quoted content."""
        payload, _ = self._guard.screen_payload(payload)
        ev = Event(
            event_id=f"ev_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            child_id=child_id,
            payload=payload,
            created_at=_now(),
        )
        with self._lock:
            self._insert_safety_event(ev)
            self._db.commit()
        return ev

    def safety_events_for(self, child_id: str) -> list[Event]:
        with self._lock:
            rows = self._db.execute(
            "SELECT event_id, event_type, child_id, payload, created_at"
            " FROM safety_events WHERE child_id = ? ORDER BY seq",
                (child_id,),
            ).fetchall()
        return [Event(r[0], r[1], r[2], json.loads(r[3]), r[4]) for r in rows]

    def _insert_event(self, ev: Event) -> None:
        self._db.execute(
            "INSERT INTO events (event_id, event_type, child_id, payload, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (ev.event_id, ev.event_type, ev.child_id, json.dumps(ev.payload), ev.created_at),
        )

    def append_idempotent(
        self, event_type: str, child_id: str, payload: dict[str, Any], idem_key: str
    ) -> Event | None:
        """Append only if idem_key was never used — the database PRIMARY KEY
        arbitrates races, so concurrent retries cannot duplicate the fact.
        Returns None when the key already existed (idempotent no-op)."""
        payload, _ = self._guard.screen_payload(payload)
        with self._lock:
            # INSERT OR IGNORE: one atomic statement, no error transaction.
            cursor = self._db.execute(
                "INSERT OR IGNORE INTO idempotency_keys (idem_key, event_id, created_at)"
                " VALUES (?, ?, ?)",
                (idem_key, "pending", _now()),
            )
            if cursor.rowcount == 0:
                self._db.rollback()
                return None
            ev = Event(
                event_id=f"ev_{uuid.uuid4().hex[:12]}",
                event_type=event_type,
                child_id=child_id,
                payload=payload,
                created_at=_now(),
            )
            self._insert_event(ev)
            self._db.execute(
                "UPDATE idempotency_keys SET event_id = ? WHERE idem_key = ?",
                (ev.event_id, idem_key),
            )
            self._db.commit()
        return ev

    def _insert_safety_event(self, ev: Event) -> None:
        self._db.execute(
            "INSERT INTO safety_events (event_id, event_type, child_id, payload, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (ev.event_id, ev.event_type, ev.child_id, json.dumps(ev.payload), ev.created_at),
        )

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
        # Traces carry full prompts and child state — screened on the way in,
        # same as events (no unredacted PII anywhere in the store).
        input_snapshot, _ = self._guard.screen_payload(input_snapshot)
        output, _ = self._guard.screen_payload(output)
        rationale, _ = self._guard.screen_payload({"r": rationale})
        rationale = rationale["r"]
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

    def decision_traces(self, child_id: str) -> list[dict[str, Any]]:
        """Public accessor for decision traces — tests and audits must not
        reach into _db."""
        with self._lock:
            rows = self._db.execute(
                "SELECT trace_id, component, input_snapshot, output, rationale, model, created_at"
                " FROM decision_trace WHERE child_id = ? ORDER BY created_at",
                (child_id,),
            ).fetchall()
        return [
            {"trace_id": r[0], "component": r[1], "input_snapshot": json.loads(r[2]),
             "output": json.loads(r[3]), "rationale": r[4], "model": r[5],
             "created_at": r[6]}
            for r in rows
        ]

    def events_for(self, child_id: str) -> list[Event]:
        with self._lock:
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
