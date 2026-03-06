from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MarketBarContract(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class NewsItemContract(BaseModel):
    headline: str
    summary: str = ''
    source: str = 'unknown'
    url: str = ''
    published_at: datetime | None = None
    symbols: list[str] = Field(default_factory=list)
    sentiment: float | None = None


class LLMMarketSnapshot(BaseModel):
    symbol: str
    timeframe: str
    as_of: datetime
    latest_price: float
    bars: list[MarketBarContract] = Field(default_factory=list)
    indicators: dict[str, float] = Field(default_factory=dict)
    news: list[NewsItemContract] = Field(default_factory=list)

