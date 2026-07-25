"""Claude provider (default, ADR-010). Lazy-imports the anthropic SDK so the
package stays importable without credentials."""

from __future__ import annotations

import json

from .base import LLMRequest, LLMResponse

DEFAULT_MODEL = "claude-sonnet-4-6"
PLANNER_MODEL = "claude-opus-4-8"


class ClaudeProvider:
    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None):
        self.model = model
        from anthropic import Anthropic  # lazy

        self._client = Anthropic(api_key=api_key)

    def complete(self, request: LLMRequest) -> LLMResponse:
        user = request.user
        if request.response_schema is not None:
            user += (
                "\n\nRespond with JSON only, valid against this JSON Schema:\n"
                + json.dumps(request.response_schema, ensure_ascii=False)
            )
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=request.system,
            messages=[{"role": "user", "content": user}],
        )
        return LLMResponse(
            content="".join(b.text for b in msg.content if b.type == "text"),
            model=self.model,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
        )
