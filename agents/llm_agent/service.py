from __future__ import annotations

from core.contracts.market_snapshot import LLMMarketSnapshot
from orchestrator.trading_cycle import TradingDecision

from .client import OpenAIClient
from .parser import parse_decision_json, to_trading_decision
from .prompt_builder import build_messages
from utils.llm_retry import execute_with_retry


class LLMAgent:
    """
    Real LLM decision engine.
    1) Build prompt from market snapshot
    2) Call OpenAI API
    3) Parse strict JSON
    4) Convert to TradingDecision
    """

    def __init__(self, client: OpenAIClient):
        self.client = client

    def analyze(self, snapshot: LLMMarketSnapshot) -> TradingDecision:
        system_prompt, user_prompt = build_messages(snapshot)

        def _task() -> TradingDecision:
            raw = self.client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
            parsed = parse_decision_json(raw)
            return to_trading_decision(symbol=snapshot.symbol, payload=parsed)

        return execute_with_retry(_task, lambda: _fallback_decision(snapshot.symbol))


def build_default_llm_agent(model: str = 'gpt-4.1-mini') -> LLMAgent:
    return LLMAgent(client=OpenAIClient(model=model))


def _fallback_decision(symbol: str) -> TradingDecision:
    return TradingDecision(
        symbol=symbol,
        action='HOLD',
        confidence=0.0,
        rationale='Fallback HOLD due to LLM failure',
        meta={'position_size': 0.0},
    )
