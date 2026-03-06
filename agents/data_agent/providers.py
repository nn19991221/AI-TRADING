from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

import requests
from alpaca.data.requests import StockLatestBarRequest

from broker.alpaca_broker import AlpacaBroker


class MarketDataProvider(Protocol):
    def fetch_market_data(self, symbol: str, lookback_bars: int, timeframe: str) -> list[dict[str, Any]]:
        ...

    def fetch_latest_price(self, symbol: str) -> float | None:
        ...


class NewsProvider(Protocol):
    def fetch_news(self, symbol: str, limit: int, start: datetime | None = None) -> list[dict[str, Any]]:
        ...


class AlpacaMarketDataProvider:
    """Reads bar and latest-price market data using the existing AlpacaBroker."""

    def __init__(self, broker: AlpacaBroker):
        self.broker = broker

    def fetch_market_data(self, symbol: str, lookback_bars: int, timeframe: str = '30Min') -> list[dict[str, Any]]:
        if timeframe != '30Min':
            raise ValueError("AlpacaMarketDataProvider currently supports timeframe='30Min' only")
        return self.broker.fetch_30m_bars(symbol=symbol, lookback_bars=lookback_bars)

    def fetch_latest_price(self, symbol: str) -> float | None:
        request = StockLatestBarRequest(symbol_or_symbols=symbol, feed=self.broker.settings.data_feed)
        result = self.broker.data.get_stock_latest_bar(request)

        bar = None
        if isinstance(result, dict):
            bar = result.get(symbol)
        elif hasattr(result, symbol):
            bar = getattr(result, symbol)
        elif hasattr(result, '__getitem__'):
            try:
                bar = result[symbol]
            except Exception:
                bar = None
        else:
            bar = result

        if not bar:
            return None
        if hasattr(bar, 'close'):
            return float(bar.close)
        if hasattr(bar, 'c'):
            return float(bar.c)
        return None


class AlpacaNewsProvider:
    """Fetches symbol news from Alpaca data REST API."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = 'https://data.alpaca.markets/v1beta1/news',
        timeout_seconds: int = 15,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def fetch_news(self, symbol: str, limit: int, start: datetime | None = None) -> list[dict[str, Any]]:
        if not self.api_key or not self.secret_key:
            return []

        params: dict[str, Any] = {'symbols': symbol, 'limit': max(1, limit)}
        if start:
            params['start'] = start.isoformat()

        headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret_key,
        }

        response = requests.get(
            self.base_url,
            params=params,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict):
            return []
        news_items = payload.get('news', [])
        if not isinstance(news_items, list):
            return []
        return news_items

