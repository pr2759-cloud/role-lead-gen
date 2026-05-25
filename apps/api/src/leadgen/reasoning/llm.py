"""Centralized Claude client with structured outputs, retry, and cost logging.

Every reasoning module calls through here — single place for cost, latency,
and prompt versioning instrumentation.
"""
import time
from typing import TypeVar, Type
from uuid import UUID
import anthropic
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from leadgen.config import settings
from leadgen.observability.llm_metering import calculate_cost

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "claude-sonnet-4-6"
FAST_MODEL = "claude-haiku-4-5-20251001"


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError)),
    )
    def structured(
        self,
        *,
        system: str,
        user: str,
        output_schema: Type[T],
        kind: str,
        prompt_version: str,
        lead_id: UUID | None = None,
        max_tokens: int = 2048,
    ) -> tuple[T, dict]:
        """Call Claude and parse the response into a Pydantic model.

        Returns (parsed_output, interaction_record). Caller persists the
        interaction_record to Postgres.
        """
        fields = list(output_schema.model_fields.keys())
        system_with_schema = (
            f"{system}\n\n"
            f"Reply with ONLY a JSON object with these keys: {fields}. No markdown, no extra text."
        )

        start = time.perf_counter()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_with_schema,
            messages=[{"role": "user", "content": user}],
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        raw_text = response.content[0].text  # type: ignore[union-attr]
        cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = output_schema.model_validate_json(cleaned)

        cost = calculate_cost(self.model, response.usage.input_tokens, response.usage.output_tokens)
        interaction = {
            "lead_id": lead_id,
            "kind": kind,
            "prompt_version": prompt_version,
            "model": self.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost_usd": cost,
            "latency_ms": latency_ms,
            "request": {"system": system, "user": user},
            "response": parsed.model_dump(mode="json"),
        }
        return parsed, interaction

    def structured_fast(
        self,
        *,
        system: str,
        user: str,
        output_schema: Type[T],
        kind: str,
        prompt_version: str,
        lead_id: UUID | None = None,
        max_tokens: int = 512,
    ) -> tuple[T, dict]:
        """Same as structured() but forces haiku for cheap analysis calls."""
        original = self.model
        self.model = FAST_MODEL
        try:
            return self.structured(
                system=system,
                user=user,
                output_schema=output_schema,
                kind=kind,
                prompt_version=prompt_version,
                lead_id=lead_id,
                max_tokens=max_tokens,
            )
        finally:
            self.model = original
