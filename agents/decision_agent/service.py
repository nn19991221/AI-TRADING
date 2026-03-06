from __future__ import annotations

from dataclasses import dataclass

from agents.market_agent.service import MarketAnalysis
from core.contracts.market_snapshot import LLMMarketSnapshot

from .client import DecisionAgentClient
from .parser import parse_decision
from .prompt_builder import build_messages
from utils.llm_retry import execute_with_retry


@dataclass
class DecisionOutput:
    action: str
    confidence: float
    position_size: float
    reasoning: str


class DecisionAgent:
    def __init__(self, client: DecisionAgentClient):
        self.client = client

    def analyze(self, snapshot: LLMMarketSnapshot, market_analysis: MarketAnalysis) -> DecisionOutput:
        system_prompt, user_prompt = build_messages(snapshot, market_analysis)

        def _task() -> DecisionOutput:
            raw = self.client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
            payload = parse_decision(raw)
            return DecisionOutput(
                action=payload.action,
                confidence=payload.confidence,
                position_size=payload.position_size,
                reasoning=payload.reasoning,
            )

        return execute_with_retry(_task, _fallback_decision)


def build_default_decision_agent(model: str | None = None) -> DecisionAgent:
    return DecisionAgent(client=DecisionAgentClient(model=model))


def _fallback_decision() -> DecisionOutput:
    return DecisionOutput(
        action='HOLD',
        confidence=0.0,
        position_size=0.0,
        reasoning='Fallback HOLD due to LLM failure',
    )
