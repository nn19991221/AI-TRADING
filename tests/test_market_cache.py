from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from state.market_cache import MarketStateCache


class MarketCacheTest(unittest.TestCase):
    def test_reuse_low_volatility_decision_for_two_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = MarketStateCache(file_path=Path(tmpdir) / 'market_cache.json')
            payload = {
                'symbol': 'AAPL',
                'market_state': 'rangebound',
                'action': 'HOLD',
                'confidence': 0.4,
                'position_size': 0.0,
                'reason': 'low vol',
            }
            cache.update('AAPL', 'low', payload)

            first = cache.get_cached_decision('AAPL', 'low')
            second = cache.get_cached_decision('AAPL', 'low')
            third = cache.get_cached_decision('AAPL', 'low')

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            self.assertIsNone(third)


if __name__ == '__main__':
    unittest.main()

