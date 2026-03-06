from __future__ import annotations

from datetime import datetime, timezone
import unittest

from core.contracts.market_snapshot import LLMMarketSnapshot
from orchestrator.trading_cycle import TradingDecision, run_cycle


class FakeDataAgent:
    def build_snapshot(self, symbol: str) -> LLMMarketSnapshot:
        now = datetime.now(timezone.utc)
        return LLMMarketSnapshot(
            symbol=symbol,
            timeframe='30Min',
            as_of=now,
            latest_price=100.0,
            bars=[],
            indicators={'sma_fast': 101.0, 'sma_slow': 99.0},
            news=[],
        )


class FakeLLMAgent:
    def analyze(self, snapshot: LLMMarketSnapshot) -> TradingDecision:
        return TradingDecision(symbol=snapshot.symbol, action='BUY', confidence=0.9)


class ApprovingRiskManager:
    def validate(self, decision: TradingDecision, snapshot: LLMMarketSnapshot):
        return True, 'APPROVED'


class RejectingRiskManager:
    def validate(self, decision: TradingDecision, snapshot: LLMMarketSnapshot):
        return False, 'DRAWDOWN_LIMIT'


class FakeExecutor:
    def __init__(self):
        self.calls = 0

    def execute(self, decision: TradingDecision, snapshot: LLMMarketSnapshot):
        self.calls += 1
        return 'accepted'


class FakePortfolioUpdater:
    def update(self):
        return {'equity': 101_000.0, 'cash': 12_000.0}


class TradingCycleTest(unittest.TestCase):
    def test_run_cycle_executes_approved_decisions(self) -> None:
        executor = FakeExecutor()
        report = run_cycle(
            ['AAPL', 'MSFT'],
            data_agent=FakeDataAgent(),
            llm_agent=FakeLLMAgent(),
            risk_manager=ApprovingRiskManager(),
            executor=executor,
            portfolio_updater=FakePortfolioUpdater(),
        )

        self.assertEqual(len(report.results), 2)
        self.assertEqual(executor.calls, 2)
        self.assertEqual(report.results[0].execution_status, 'accepted')
        self.assertEqual(report.results[1].risk_reason, 'APPROVED')
        self.assertIn('equity', report.portfolio_state)

    def test_run_cycle_skips_rejected_decisions(self) -> None:
        executor = FakeExecutor()
        report = run_cycle(
            ['AAPL'],
            data_agent=FakeDataAgent(),
            llm_agent=FakeLLMAgent(),
            risk_manager=RejectingRiskManager(),
            executor=executor,
            portfolio_updater=FakePortfolioUpdater(),
        )

        self.assertEqual(len(report.results), 1)
        self.assertEqual(executor.calls, 0)
        self.assertFalse(report.results[0].approved)
        self.assertEqual(report.results[0].execution_status, 'SKIPPED_RISK_REJECTED')


if __name__ == '__main__':
    unittest.main()

