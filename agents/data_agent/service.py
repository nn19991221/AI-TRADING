from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from broker.alpaca_broker import AlpacaBroker
from config.settings import Settings, get_settings
from core.contracts.market_snapshot import LLMMarketSnapshot, MarketBarContract, NewsItemContract

from .indicators import compute_indicators
from .providers import AlpacaMarketDataProvider, AlpacaNewsProvider, MarketDataProvider, NewsProvider


class DataAgent:
    """Collects market/news context and outputs an LLM-ready structured snapshot."""

    def __init__(self, market_provider: MarketDataProvider, news_provider: NewsProvider):
        self.market_provider = market_provider
        self.news_provider = news_provider

    def fetch_market_data(
        self,
        symbol: str,
        lookback_bars: int = 100,
        timeframe: str = '30Min',
    ) -> list[MarketBarContract]:
        raw_bars = self.market_provider.fetch_market_data(
            symbol=symbol,
            lookback_bars=lookback_bars,
            timeframe=timeframe,
        )
        bars = [self._normalize_bar(symbol=symbol, row=row) for row in raw_bars]
        bars = [bar for bar in bars if bar is not None]
        bars.sort(key=lambda bar: bar.timestamp)
        return bars

    def fetch_news(
        self,
        symbol: str,
        limit: int = 10,
        lookback_hours: int = 24,
    ) -> list[NewsItemContract]:
        start = datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))
        try:
            raw_news = self.news_provider.fetch_news(symbol=symbol, limit=limit, start=start)
        except Exception:
            raw_news = []
        normalized = [self._normalize_news_item(symbol=symbol, item=item) for item in raw_news]
        return [item for item in normalized if item is not None]

    def compute_indicators(
        self,
        bars: list[MarketBarContract],
        fast_window: int = 5,
        slow_window: int = 20,
        rsi_window: int = 14,
        volatility_window: int = 20,
    ) -> dict[str, float]:
        closes = [bar.close for bar in bars]
        return compute_indicators(
            closes=closes,
            fast_window=fast_window,
            slow_window=slow_window,
            rsi_window=rsi_window,
            volatility_window=volatility_window,
        )

    def build_snapshot(
        self,
        symbol: str,
        lookback_bars: int = 100,
        timeframe: str = '30Min',
        news_limit: int = 10,
        news_lookback_hours: int = 24,
        fast_window: int = 5,
        slow_window: int = 20,
        rsi_window: int = 14,
        volatility_window: int = 20,
    ) -> LLMMarketSnapshot:
        bars = self.fetch_market_data(symbol=symbol, lookback_bars=lookback_bars, timeframe=timeframe)
        news = self.fetch_news(symbol=symbol, limit=news_limit, lookback_hours=news_lookback_hours)
        indicators = self.compute_indicators(
            bars=bars,
            fast_window=fast_window,
            slow_window=slow_window,
            rsi_window=rsi_window,
            volatility_window=volatility_window,
        )

        latest_price = bars[-1].close if bars else (self.market_provider.fetch_latest_price(symbol) or 0.0)
        as_of = bars[-1].timestamp if bars else datetime.now(timezone.utc)

        return LLMMarketSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            as_of=as_of,
            latest_price=latest_price,
            bars=bars,
            indicators=indicators,
            news=news,
        )

    @staticmethod
    def to_llm_payload(snapshot: LLMMarketSnapshot) -> dict[str, Any]:
        return snapshot.model_dump(mode='json')

    @staticmethod
    def _normalize_bar(symbol: str, row: dict[str, Any]) -> MarketBarContract | None:
        try:
            timestamp = _coerce_datetime(row.get('timestamp'))
            return MarketBarContract(
                symbol=str(row.get('symbol') or symbol).upper(),
                timestamp=timestamp,
                open=float(row.get('open')),
                high=float(row.get('high')),
                low=float(row.get('low')),
                close=float(row.get('close')),
                volume=int(row.get('volume')),
            )
        except Exception:
            return None

    @staticmethod
    def _normalize_news_item(symbol: str, item: dict[str, Any]) -> NewsItemContract | None:
        headline = str(item.get('headline') or item.get('title') or '').strip()
        if not headline:
            return None

        published_raw = item.get('created_at') or item.get('updated_at') or item.get('published_at')
        published_at = _coerce_datetime(published_raw) if published_raw else None

        raw_symbols = item.get('symbols') if isinstance(item.get('symbols'), list) else [symbol]
        symbols = [str(value).upper() for value in raw_symbols if str(value).strip()]

        return NewsItemContract(
            headline=headline,
            summary=str(item.get('summary') or ''),
            source=str(item.get('source') or item.get('author') or 'unknown'),
            url=str(item.get('url') or ''),
            published_at=published_at,
            symbols=symbols,
        )


def build_default_data_agent(settings: Settings | None = None) -> DataAgent:
    settings = settings or get_settings()
    broker = AlpacaBroker(settings=settings)
    market_provider = AlpacaMarketDataProvider(broker=broker)
    news_provider = AlpacaNewsProvider(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
    )
    return DataAgent(market_provider=market_provider, news_provider=news_provider)


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value)
    if text.endswith('Z'):
        text = text.replace('Z', '+00:00')
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

