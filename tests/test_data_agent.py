from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from agents.data_agent.service import DataAgent


class FakeMarketProvider:
    def __init__(self, bars: list[dict], latest_price: float = 0.0):
        self._bars = bars
        self._latest_price = latest_price

    def fetch_market_data(self, symbol: str, lookback_bars: int, timeframe: str):
        return self._bars[-lookback_bars:]

    def fetch_latest_price(self, symbol: str):
        return self._latest_price


class FakeNewsProvider:
    def __init__(self, news_items: list[dict]):
        self._news_items = news_items

    def fetch_news(self, symbol: str, limit: int, start=None):
        return self._news_items[:limit]


class DataAgentTest(unittest.TestCase):
    def test_build_snapshot_outputs_structured_payload(self) -> None:
        start = datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc)
        bars = [
            {
                'symbol': 'AAPL',
                'timestamp': start + timedelta(minutes=30 * i),
                'open': 100 + i,
                'high': 101 + i,
                'low': 99 + i,
                'close': 100 + i,
                'volume': 1000 + i,
            }
            for i in range(30)
        ]
        news_items = [
            {
                'headline': 'Apple launches new product',
                'summary': 'A short company update',
                'source': 'newswire',
                'url': 'https://example.com/story',
                'created_at': start.isoformat(),
                'symbols': ['AAPL'],
            }
        ]

        agent = DataAgent(
            market_provider=FakeMarketProvider(bars=bars, latest_price=130.0),
            news_provider=FakeNewsProvider(news_items=news_items),
        )
        snapshot = agent.build_snapshot(symbol='AAPL')

        self.assertEqual(snapshot.symbol, 'AAPL')
        self.assertEqual(snapshot.timeframe, '30Min')
        self.assertEqual(len(snapshot.bars), 30)
        self.assertEqual(len(snapshot.news), 1)
        self.assertIn('sma_fast', snapshot.indicators)
        self.assertIn('sma_slow', snapshot.indicators)
        self.assertGreater(snapshot.latest_price, 0)

        payload = agent.to_llm_payload(snapshot)
        self.assertEqual(payload['symbol'], 'AAPL')
        self.assertIn('bars', payload)
        self.assertIn('news', payload)
        self.assertIn('indicators', payload)

    def test_build_snapshot_without_bars_falls_back_to_latest_price(self) -> None:
        agent = DataAgent(
            market_provider=FakeMarketProvider(bars=[], latest_price=222.5),
            news_provider=FakeNewsProvider(news_items=[]),
        )

        snapshot = agent.build_snapshot(symbol='MSFT')

        self.assertEqual(snapshot.symbol, 'MSFT')
        self.assertEqual(snapshot.latest_price, 222.5)
        self.assertEqual(len(snapshot.bars), 0)
        self.assertEqual(len(snapshot.news), 0)
        self.assertEqual(snapshot.indicators, {})


if __name__ == '__main__':
    unittest.main()

