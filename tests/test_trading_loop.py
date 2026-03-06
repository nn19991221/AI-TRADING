from __future__ import annotations

import unittest

from app.trading_loop import _sanitize_interval


class TradingLoopTest(unittest.TestCase):
    def test_sanitize_interval_valid_range(self) -> None:
        self.assertEqual(_sanitize_interval(1), 1)
        self.assertEqual(_sanitize_interval(15), 15)

    def test_sanitize_interval_fallback(self) -> None:
        self.assertEqual(_sanitize_interval(None), 5)
        self.assertEqual(_sanitize_interval(0), 5)
        self.assertEqual(_sanitize_interval(16), 5)
        self.assertEqual(_sanitize_interval('bad'), 5)


if __name__ == '__main__':
    unittest.main()

