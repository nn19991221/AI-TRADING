from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from core.contracts.market_snapshot import LLMMarketSnapshot, MarketBarContract
from utils.market_summary import build_market_summary


class MarketSummaryTest(unittest.TestCase):
    def test_build_market_summary(self) -> None:
        start = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
        bars = [
            MarketBarContract(
                symbol='AAPL',
                timestamp=start + timedelta(minutes=30 * i),
                open=100 + i,
                high=101 + i,
                low=99 + i,
                close=100 + i,
                volume=1000 + i * 10,
            )
            for i in range(10)
        ]
        snapshot = LLMMarketSnapshot(
            symbol='AAPL',
            timeframe='30Min',
            as_of=bars[-1].timestamp,
            latest_price=bars[-1].close,
            bars=bars,
            indicators={'sma_fast': 108.0, 'sma_slow': 105.0, 'return_1': 0.01, 'volatility': 0.01},
            news=[],
        )
        summary = build_market_summary(snapshot)
        self.assertEqual(summary['trend'], 'uptrend')
        self.assertEqual(summary['momentum'], 'positive')
        self.assertIn(summary['volatility'], {'low', 'medium', 'high'})
        self.assertIn('volume_spike', summary)


if __name__ == '__main__':
    unittest.main()

