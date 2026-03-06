from __future__ import annotations

from datetime import datetime, timezone
import unittest

from agents.strategy_agent.service import StrategyAgent
from core.contracts.market_snapshot import LLMMarketSnapshot


class FakeStrategyClient:
    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        return (
            '{"decisions":['
            '{"symbol":"AAPL","market_state":"trending_up","action":"BUY","confidence":0.8,"position_size":0.15,"reason":"momentum strong"},'
            '{"symbol":"MSFT","market_state":"rangebound","action":"HOLD","confidence":0.55,"position_size":0.05,"reason":"mixed signals"}'
            ']}'
        )


class StrategyAgentTest(unittest.TestCase):
    def _snapshot(self, symbol: str) -> LLMMarketSnapshot:
        return LLMMarketSnapshot(
            symbol=symbol,
            timeframe='30Min',
            as_of=datetime.now(timezone.utc),
            latest_price=100.0,
            bars=[],
            indicators={'return_1': 0.01, 'volatility': 0.01},
            news=[],
        )

    def test_analyze_batch_returns_decisions(self) -> None:
        agent = StrategyAgent(client=FakeStrategyClient())
        out = agent.analyze_batch({'AAPL': self._snapshot('AAPL'), 'MSFT': self._snapshot('MSFT')})
        self.assertEqual(out['AAPL'].action, 'BUY')
        self.assertEqual(out['MSFT'].action, 'HOLD')
        self.assertEqual(out['AAPL'].market_state, 'trending_up')


if __name__ == '__main__':
    unittest.main()

