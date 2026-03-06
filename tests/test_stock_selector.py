from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from agents.stock_selector.service import StockSelector
from agents.stock_selector.universe import TradingUniverseBuilder
from core.contracts.market_snapshot import LLMMarketSnapshot, MarketBarContract, NewsItemContract


def _bars(base_price: float, slope: float, volume_base: int, count: int = 30) -> list[MarketBarContract]:
    start = datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc)
    items: list[MarketBarContract] = []
    for i in range(count):
        close = base_price + slope * i
        items.append(
            MarketBarContract(
                symbol='X',
                timestamp=start + timedelta(minutes=30 * i),
                open=close - 0.3,
                high=close + 0.5,
                low=close - 0.8,
                close=close,
                volume=volume_base + (3000 if i == count - 1 else i * 10),
            )
        )
    return items


class FakeDataAgent:
    def __init__(self, snapshots: dict[str, LLMMarketSnapshot]):
        self.snapshots = snapshots

    def build_snapshot(self, symbol: str) -> LLMMarketSnapshot:
        return self.snapshots[symbol]


class StockSelectorTest(unittest.TestCase):
    def test_select_symbols_returns_top_ranked_candidates(self) -> None:
        now = datetime.now(timezone.utc)
        snapshots = {
            'AAA': LLMMarketSnapshot(
                symbol='AAA',
                timeframe='30Min',
                as_of=now,
                latest_price=120.0,
                bars=_bars(base_price=100.0, slope=0.9, volume_base=1000),
                indicators={},
                news=[NewsItemContract(headline='AAA beats estimates', summary='strong growth', source='wire')],
            ),
            'BBB': LLMMarketSnapshot(
                symbol='BBB',
                timeframe='30Min',
                as_of=now,
                latest_price=95.0,
                bars=_bars(base_price=100.0, slope=-0.2, volume_base=1000),
                indicators={},
                news=[NewsItemContract(headline='BBB faces lawsuit', summary='weak outlook', source='wire')],
            ),
            'CCC': LLMMarketSnapshot(
                symbol='CCC',
                timeframe='30Min',
                as_of=now,
                latest_price=150.0,
                bars=_bars(base_price=120.0, slope=0.4, volume_base=1000),
                indicators={},
                news=[],
            ),
        }

        selector = StockSelector(
            data_agent=FakeDataAgent(snapshots),
            universe_builder=TradingUniverseBuilder(static_symbols=['AAA', 'BBB', 'CCC']),
            top_n=2,
            min_bars=25,
        )

        selected = selector.select_symbols()
        self.assertEqual(len(selected), 2)
        self.assertIn('AAA', selected)
        self.assertIn('CCC', selected)
        self.assertNotIn('BBB', selected)

    def test_build_universe_dedupes_and_normalizes(self) -> None:
        universe = TradingUniverseBuilder(static_symbols=['aapl', 'AAPL', ' msft ', '', 'MSFT'])
        symbols = universe.build_trading_universe()
        self.assertEqual(symbols, ['AAPL', 'MSFT'])


if __name__ == '__main__':
    unittest.main()

