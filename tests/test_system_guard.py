from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from orchestrator.trading_cycle import TradingDecision
from risk.system_guard import SystemGuard


class SystemGuardTest(unittest.TestCase):
    def test_blocks_when_position_size_exceeds_limit(self) -> None:
        guard = SystemGuard()
        decision = TradingDecision(symbol='AAPL', action='BUY', meta={'position_size': 0.5})
        result = guard.pre_trade_check(decision, now=datetime.now(timezone.utc))
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, 'SYSTEM_GUARD_MAX_POSITION_SIZE')

    def test_blocks_when_trade_rate_exceeds_limit(self) -> None:
        guard = SystemGuard()
        now = datetime.now(timezone.utc)
        for i in range(20):
            guard.record_trade(now=now - timedelta(minutes=1) + timedelta(seconds=i))
        decision = TradingDecision(symbol='MSFT', action='BUY', meta={'position_size': 0.1})
        result = guard.pre_trade_check(decision, now=now)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, 'SYSTEM_GUARD_MAX_TRADES_PER_HOUR')


if __name__ == '__main__':
    unittest.main()

