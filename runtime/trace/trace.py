"""Decision Trace wrapper (ADR-010, Invariant 6).

Every LLM call flows through TrackedProvider so every judgment is logged:
why, based on what, from which evidence.

Contract discipline: when the request carries a response_schema, the
response is validated BEFORE the trace is written — an invalid judgment
must not be immortalized as if it were a decision.
"""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft7Validator

from ..contracts import ContractViolation
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
        """Call the provider, validate the response against the request's
        response_schema (if any), THEN log the decision trace."""
        resp = self._provider.complete(request)
        if request.response_schema is not None:
            try:
                parsed = json.loads(resp.content)
            except json.JSONDecodeError as e:
                raise ContractViolation(
                    f"{self._component}: LLM response is not JSON: {e}") from e
            errors = sorted(
                Draft7Validator(request.response_schema).iter_errors(parsed),
                key=lambda e: list(e.path))
            if errors:
                raise ContractViolation(
                    f"{self._component}: LLM response violates response_schema: "
                    f"{errors[0].message}")
        trace_id = self._store.trace(
            self._component,
            input_snapshot={"system": request.system, "user": request.user,
                            "context": context or {}},
            output={"content": resp.content},
            child_id=child_id,
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
        )
        return resp, trace_id
