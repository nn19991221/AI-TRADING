from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from risk.circuit_breaker import CircuitBreaker


class CircuitBreakerTest(unittest.TestCase):
    def test_pauses_after_consecutive_losses(self) -> None:
        breaker = CircuitBreaker()
        now = datetime.now(timezone.utc)
        breaker.update_after_cycle(portfolio_state={'equity': 100_000.0, 'daily_pnl': 0.0}, trades_executed=1, now=now)
        for i in range(5):
            status = breaker.update_after_cycle(
                portfolio_state={'equity': 99_000.0 - i * 100, 'daily_pnl': -100.0},
                trades_executed=1,
                now=now + timedelta(minutes=i + 1),
            )
        self.assertTrue(status.paused)
        self.assertEqual(status.reason, 'CIRCUIT_BREAKER_CONSECUTIVE_LOSSES')

    def test_pauses_on_drawdown(self) -> None:
        breaker = CircuitBreaker()
        now = datetime.now(timezone.utc)
        breaker.update_after_cycle(portfolio_state={'equity': 100_000.0, 'daily_pnl': 0.0}, trades_executed=0, now=now)
        status = breaker.update_after_cycle(
            portfolio_state={'equity': 91_000.0, 'daily_pnl': -9_000.0},
            trades_executed=0,
            now=now + timedelta(minutes=1),
        )
        self.assertTrue(status.paused)
        self.assertEqual(status.reason, 'CIRCUIT_BREAKER_DRAWDOWN')


if __name__ == '__main__':
    unittest.main()

