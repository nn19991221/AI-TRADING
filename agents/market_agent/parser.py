from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agents.llm_agent.parser import _extract_json_object


class MarketAnalysisPayload(BaseModel):
    trend: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    momentum: float = Field(ge=-1.0, le=1.0)
    volatility_regime: Literal['LOW', 'MEDIUM', 'HIGH']
    news_sentiment: float = Field(ge=-1.0, le=1.0)
    summary: str = Field(min_length=1)


def parse_market_analysis(raw: str) -> MarketAnalysisPayload:
    payload = _extract_json_object(raw)
    return MarketAnalysisPayload.model_validate(payload)

