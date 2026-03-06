from __future__ import annotations

from dataclasses import dataclass

from core.contracts.market_snapshot import LLMMarketSnapshot

from .client import MarketAgentClient
from .parser import parse_market_analysis
from .prompt_builder import build_messages
from utils.llm_retry import execute_with_retry


@dataclass
class MarketAnalysis:
    trend: str
    momentum: float
    volatility_regime: str
    news_sentiment: float
    summary: str


class MarketAnalysisAgent:
    def __init__(self, client: MarketAgentClient):
        self.client = client

    def analyze(self, snapshot: LLMMarketSnapshot) -> MarketAnalysis:
        system_prompt, user_prompt = build_messages(snapshot)

        def _task() -> MarketAnalysis:
            raw = self.client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
            payload = parse_market_analysis(raw)
            return MarketAnalysis(
                trend=payload.trend,
                momentum=payload.momentum,
                volatility_regime=payload.volatility_regime,
                news_sentiment=payload.news_sentiment,
                summary=payload.summary,
            )

        return execute_with_retry(_task, _fallback_market_analysis)


def build_default_market_agent(model: str | None = None) -> MarketAnalysisAgent:
    return MarketAnalysisAgent(client=MarketAgentClient(model=model))


def _fallback_market_analysis() -> MarketAnalysis:
    return MarketAnalysis(
        trend='NEUTRAL',
        momentum=0.0,
        volatility_regime='MEDIUM',
        news_sentiment=0.0,
        summary='Fallback analysis due to LLM failure',
    )
