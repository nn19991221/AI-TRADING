from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.contracts.market_snapshot import LLMMarketSnapshot

from .client import RiskAgentClient
from .parser import parse_risk_response
from .prompt_builder import build_messages
from utils.llm_retry import execute_with_retry


@dataclass
class RiskAssessment:
    approved: bool
    reason: str
    adjusted_action: str
    max_position_size: float


class DecisionLike(Protocol):
    def normalized_action(self) -> str:
        ...


class RiskAgent:
    def __init__(self, client: RiskAgentClient):
        self.client = client

    def assess(self, snapshot: LLMMarketSnapshot, decision: DecisionLike) -> RiskAssessment:
        system_prompt, user_prompt = build_messages(snapshot, decision)

        def _task() -> RiskAssessment:
            raw = self.client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
            payload = parse_risk_response(raw)
            return RiskAssessment(
                approved=payload.approved,
                reason=payload.reason,
                adjusted_action=payload.adjusted_action,
                max_position_size=payload.max_position_size,
            )

        return execute_with_retry(_task, _fallback_risk_assessment)


def build_default_risk_agent(model: str | None = None) -> RiskAgent:
    return RiskAgent(client=RiskAgentClient(model=model))


def _fallback_risk_assessment() -> RiskAssessment:
    return RiskAssessment(
        approved=False,
        reason='Fallback HOLD due to LLM failure',
        adjusted_action='HOLD',
        max_position_size=0.0,
    )
