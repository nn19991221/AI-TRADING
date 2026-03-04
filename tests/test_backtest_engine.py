from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from backtest.engine import BacktestEngine
from backtest.models import Bar
from risk.risk_manager import RiskManager
from strategy.ma_crossover import MovingAverageCrossoverStrategy


class BacktestEngineTest(unittest.TestCase):
    def test_order_fills_on_next_bar_open_and_generates_metrics(self) -> None:
        start = datetime(2024, 1, 2, 9, 30)
        bars = [
            Bar('AAPL', start + timedelta(minutes=30 * i), o, o + 1, o - 1, c, 1000)
            for i, (o, c) in enumerate(
                [
                    (100, 100),
                    (101, 102),
                    (103, 104),
                    (105, 106),
                    (107, 108),
                    (109, 110),
                ]
            )
        ]

        strategy = MovingAverageCrossoverStrategy(fast_window=2, slow_window=3)
        risk = RiskManager(max_position_pct=0.5, max_daily_drawdown_pct=0.9)
        engine = BacktestEngine(strategy=strategy, risk_manager=risk, initial_cash=10_000)

        report = engine.run({'AAPL': bars})

        self.assertGreater(len(report.trade_log), 0)
        first_trade = report.trade_log[0]
        self.assertEqual(first_trade.submitted_at, bars[2].timestamp)
        self.assertEqual(first_trade.filled_at, bars[3].timestamp)
        self.assertGreater(len(report.equity_curve), 0)
        self.assertGreaterEqual(report.max_drawdown, 0.0)


if __name__ == '__main__':
    unittest.main()
