"""Callback aggregate — owns the (session, moment) state machine.

not_shown → shown → recognized|ignored. Transitions are ATOMIC
(EventStore.append_idempotent: the database key arbitrates races), so
concurrent retries cannot double-write. ChildEngine submits commands;
this module interprets the Relationship Event Stream (review6).
"""

from __future__ import annotations

from ..contracts import ContractViolation
from ..events.store import EventStore


def _history(events: list, session_id: str, moment: str) -> tuple[bool, bool]:
    shown = answered = False
    for e in events:
        p = e.payload
        if p.get("session_id") != session_id or p.get("moment") != moment:
            continue
        if e.event_type == "partner.callback_offered":
            shown = True
        elif e.event_type == "partner.callback_answered":
            answered = True
    return shown, answered


def apply_callback(
    store: EventStore,
    *,
    child_id: str,
    session_id: str,
    moment: str,
    transition: str,
    launch_source: str,
    date: str,
    response: str | None = None,
) -> bool:
    """Apply one callback transition. Returns True if a new fact was
    written, False for an idempotent no-op. Out-of-order transitions are
    hard violations."""
    events = store.events_for(child_id)
    shown, answered = _history(events, session_id, moment)
    base = {"moment": moment, "session_id": session_id,
            "launch_source": launch_source, "date": date}
    if transition == "shown":
        return store.append_idempotent(
            "partner.callback_offered", child_id, base,
            idem_key=f"{child_id}:{session_id}:{moment}:shown") is not None
    if transition == "answered":
        if not shown:
            raise ContractViolation("callback recognized before it was shown")
        if response not in ("recognized", "ignored"):
            raise ContractViolation(f"invalid callback response: {response}")
        return None if answered else store.append_idempotent(
            "partner.callback_answered", child_id,
            {**base, "response": response},
            idem_key=f"{child_id}:{session_id}:{moment}:answered") is not None
    raise ValueError(f"unknown callback transition: {transition}")


def session_launch_source(events: list, session_id: str) -> str | None:
    for e in events:
        if (e.event_type == "session.started"
                and e.payload.get("session_id") == session_id):
            return e.payload.get("launch_source")
    return None
