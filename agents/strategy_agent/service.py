from __future__ import annotations

from dataclasses import dataclass

from core.contracts.market_snapshot import LLMMarketSnapshot
from utils.llm_retry import execute_with_retry
from utils.market_summary import build_market_summary

from .client import StrategyAgentClient
from .parser import parse_strategy_batch
from .prompt_builder import build_messages, compact_snapshot_payload


@dataclass
class StrategyDecision:
    symbol: str
    market_state: str
    action: str
    confidence: float
    position_size: float
    reason: str


class StrategyAgent:
    def __init__(self, client: StrategyAgentClient):
        self.client = client

    def analyze(self, snapshot: LLMMarketSnapshot) -> StrategyDecision:
        decisions = self.analyze_batch({snapshot.symbol: snapshot})
        return decisions.get(snapshot.symbol, _fallback_decision(snapshot.symbol))

    def analyze_batch(self, snapshots: dict[str, LLMMarketSnapshot]) -> dict[str, StrategyDecision]:
        if not snapshots:
            return {}

        compact_rows = []
        symbols = []
        for symbol, snapshot in snapshots.items():
            symbols.append(symbol)
            summary = build_market_summary(snapshot)
            compact_rows.append(compact_snapshot_payload(snapshot, summary))

        system_prompt, user_prompt = build_messages(compact_rows)

        def _task() -> dict[str, StrategyDecision]:
            raw = self.client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
            payload = parse_strategy_batch(raw)
            out: dict[str, StrategyDecision] = {}
            for item in payload.decisions:
                out[item.symbol.upper()] = StrategyDecision(
                    symbol=item.symbol.upper(),
                    market_state=item.market_state,
                    action=item.action,
                    confidence=item.confidence,
                    position_size=item.position_size,
                    reason=item.reason,
                )
            return out

        fallback = lambda: {symbol.upper(): _fallback_decision(symbol.upper()) for symbol in symbols}
        parsed = execute_with_retry(_task, fallback)
        for symbol in symbols:
            parsed.setdefault(symbol.upper(), _fallback_decision(symbol.upper()))
        return parsed


def build_default_strategy_agent(model: str | None = None) -> StrategyAgent:
    return StrategyAgent(client=StrategyAgentClient(model=model))


def _fallback_decision(symbol: str) -> StrategyDecision:
    return StrategyDecision(
        symbol=symbol.upper(),
        market_state='rangebound',
        action='HOLD',
        confidence=0.0,
        position_size=0.0,
        reason='Fallback HOLD due to LLM failure',
    )

