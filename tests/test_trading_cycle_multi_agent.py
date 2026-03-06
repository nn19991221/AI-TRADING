from __future__ import annotations

from datetime import datetime, timezone
import unittest

from core.contracts.market_snapshot import LLMMarketSnapshot
from orchestrator.trading_cycle import run_cycle


class FakeDataAgent:
    def build_snapshot(self, symbol: str) -> LLMMarketSnapshot:
        return LLMMarketSnapshot(
            symbol=symbol,
            timeframe='30Min',
            as_of=datetime.now(timezone.utc),
            latest_price=100.0,
            bars=[],
            indicators={},
            news=[],
        )


class FakeMarketAgent:
    def analyze(self, snapshot: LLMMarketSnapshot):
        return {'trend': 'BULLISH'}


class FakeDecisionAgent:
    def analyze(self, snapshot: LLMMarketSnapshot, market_analysis):
        return {
            'action': 'BUY',
            'confidence': 0.8,
            'position_size': 0.2,
            'reasoning': 'test decision',
        }


class FakeRiskAgent:
    def assess(self, snapshot: LLMMarketSnapshot, decision):
        return {
            'approved': True,
            'reason': 'APPROVED',
            'adjusted_action': decision.action,
            'max_position_size': 0.2,
        }


class FakeExecutor:
    def execute(self, decision, snapshot):
        return 'accepted'


class FakePortfolioUpdater:
    def update(self):
        return {'equity': 1_000.0}


class FakeFrequencyAgent:
    def recommend(self, results, portfolio_state):
        return {'next_check_minutes': 12, 'reason': 'High volatility'}


class FailingFrequencyAgent:
    def recommend(self, results, portfolio_state):
        raise RuntimeError('frequency error')


class InvalidFrequencyAgent:
    def recommend(self, results, portfolio_state):
        return {'next_check_minutes': 60, 'reason': 'too slow'}


class TradingCycleMultiAgentTest(unittest.TestCase):
    def test_run_cycle_with_specialized_agents(self) -> None:
        report = run_cycle(
            ['AAPL'],
            data_agent=FakeDataAgent(),
            market_agent=FakeMarketAgent(),
            decision_agent=FakeDecisionAgent(),
            risk_agent=FakeRiskAgent(),
            executor=FakeExecutor(),
            portfolio_updater=FakePortfolioUpdater(),
            frequency_agent=FakeFrequencyAgent(),
        )
        self.assertEqual(len(report.results), 1)
        self.assertTrue(report.results[0].approved)
        self.assertEqual(report.next_check_minutes, 12)
        self.assertEqual(report.frequency_reason, 'High volatility')

    def test_run_cycle_frequency_fallback_to_five_minutes(self) -> None:
        report = run_cycle(
            ['AAPL'],
            data_agent=FakeDataAgent(),
            market_agent=FakeMarketAgent(),
            decision_agent=FakeDecisionAgent(),
            risk_agent=FakeRiskAgent(),
            executor=FakeExecutor(),
            portfolio_updater=FakePortfolioUpdater(),
            frequency_agent=FailingFrequencyAgent(),
        )
        self.assertEqual(report.next_check_minutes, 5)
        self.assertIn('Fallback 5m', report.frequency_reason)

    def test_run_cycle_frequency_invalid_interval_fallback(self) -> None:
        report = run_cycle(
            ['AAPL'],
            data_agent=FakeDataAgent(),
            market_agent=FakeMarketAgent(),
            decision_agent=FakeDecisionAgent(),
            risk_agent=FakeRiskAgent(),
            executor=FakeExecutor(),
            portfolio_updater=FakePortfolioUpdater(),
            frequency_agent=InvalidFrequencyAgent(),
        )
        self.assertEqual(report.next_check_minutes, 5)
        self.assertIn('Fallback 5m', report.frequency_reason)


if __name__ == '__main__':
    unittest.main()
