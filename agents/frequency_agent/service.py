from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .client import FrequencyAgentClient
from .parser import parse_frequency_response
from .prompt_builder import build_messages
from utils.llm_retry import execute_with_retry


@dataclass
class FrequencyDecision:
    next_check_minutes: int
    reason: str


class FrequencyAgent:
    def __init__(self, client: FrequencyAgentClient):
        self.client = client

    def recommend(
        self,
        results: list[dict[str, Any]],
        portfolio_state: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> FrequencyDecision:
        system_prompt, user_prompt = build_messages(
            results=results,
            portfolio_state=portfolio_state,
            context=context,
        )

        def _task() -> FrequencyDecision:
            raw = self.client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
            payload = parse_frequency_response(raw)
            return FrequencyDecision(
                next_check_minutes=payload.next_check_minutes,
                reason=payload.reason,
            )

        return execute_with_retry(_task, _fallback_frequency)


def build_default_frequency_agent(model: str | None = None) -> FrequencyAgent:
    return FrequencyAgent(client=FrequencyAgentClient(model=model))


def _fallback_frequency() -> FrequencyDecision:
    return FrequencyDecision(next_check_minutes=5, reason='Fallback interval due to LLM failure')
