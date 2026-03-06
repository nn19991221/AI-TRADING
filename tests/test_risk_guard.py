from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from orchestrator.trading_cycle import TradingDecision
from risk.risk_guard import RiskGuard


class RiskGuardTest(unittest.TestCase):
    def test_blocks_large_position_size(self) -> None:
        guard = RiskGuard()
        decision = TradingDecision(symbol='AAPL', action='BUY', meta={'position_size': 0.3})
        result = guard.validate(decision, now=datetime.now(timezone.utc))
        self.assertFalse(result.approved)
        self.assertEqual(result.action, 'HOLD')
        self.assertEqual(result.reason, 'MAX_POSITION_SIZE_EXCEEDED')

    def test_blocks_max_trades_per_hour(self) -> None:
        guard = RiskGuard()
        now = datetime.now(timezone.utc)
        for i in range(20):
            guard.record_trade(now=now - timedelta(minutes=10) + timedelta(seconds=i))

        decision = TradingDecision(symbol='MSFT', action='BUY', meta={'position_size': 0.1})
        result = guard.validate(decision, now=now)
        self.assertFalse(result.approved)
        self.assertEqual(result.reason, 'MAX_TRADES_PER_HOUR_EXCEEDED')

    def test_blocks_daily_loss(self) -> None:
        guard = RiskGuard()
        now = datetime.now(timezone.utc)
        guard.update_portfolio({'equity': 100_000.0}, now=now)
        guard.update_portfolio({'equity': 85_000.0}, now=now + timedelta(minutes=5))
        decision = TradingDecision(symbol='NVDA', action='BUY', meta={'position_size': 0.1})
        result = guard.validate(decision, now=now + timedelta(minutes=6))
        self.assertFalse(result.approved)
        self.assertEqual(result.reason, 'MAX_DAILY_LOSS_EXCEEDED')


if __name__ == '__main__':
    unittest.main()

