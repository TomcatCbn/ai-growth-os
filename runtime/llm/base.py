"""LLM provider abstraction (ADR-010).

No component may call an LLM except through `runtime.trace.TrackedProvider`.
Model-agnostic; Claude is the default. Tier guidance: Sonnet for
extraction/generation, Opus for Planner decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class LLMRequest:
    system: str
    user: str
    # JSON Schema the response must validate against (JSON mode + schema
    # validation on every response).
    response_schema: dict[str, Any] | None = None
    max_tokens: int = 4096
    temperature: float = 0.0


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    model: str

    def complete(self, request: LLMRequest) -> LLMResponse: ...
