"""Decision Trace wrapper (ADR-010, Invariant 6).

Every LLM call flows through TrackedProvider so every judgment is logged:
why, based on what, from which evidence.
"""

from __future__ import annotations

from typing import Any

from ..events.store import EventStore
from ..llm.base import LLMProvider, LLMRequest, LLMResponse


class TrackedProvider:
    def __init__(self, provider: LLMProvider, store: EventStore, component: str):
        self._provider = provider
        self._store = store
        self._component = component

    @property
    def model(self) -> str:
        return self._provider.model

    def complete(
        self,
        request: LLMRequest,
        *,
        child_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[LLMResponse, str]:
        """Call the provider and log a decision trace. Returns (response, trace_id)."""
        resp = self._provider.complete(request)
        trace_id = self._store.trace(
            self._component,
            input_snapshot={"system": request.system, "user": request.user, "context": context or {}},
            output={"content": resp.content},
            child_id=child_id,
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
        )
        return resp, trace_id
