from __future__ import annotations

from datetime import datetime, timezone
import unittest

from agents.llm_agent.parser import parse_decision_json
from agents.llm_agent.service import LLMAgent
from core.contracts.market_snapshot import LLMMarketSnapshot


class FakeOpenAIClient:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        return self.response_text


class LLMAgentTest(unittest.TestCase):
    def _snapshot(self) -> LLMMarketSnapshot:
        return LLMMarketSnapshot(
            symbol='AAPL',
            timeframe='30Min',
            as_of=datetime.now(timezone.utc),
            latest_price=188.2,
            bars=[],
            indicators={'sma_fast': 189.0, 'sma_slow': 186.0},
            news=[],
        )

    def test_parser_accepts_valid_json(self) -> None:
        raw = '{"action":"BUY","confidence":0.83,"position_size":0.25,"reasoning":"Trend and momentum are positive."}'
        parsed = parse_decision_json(raw)
        self.assertEqual(parsed.action, 'BUY')
        self.assertAlmostEqual(parsed.confidence, 0.83, places=6)
        self.assertAlmostEqual(parsed.position_size, 0.25, places=6)

    def test_parser_rejects_invalid_action(self) -> None:
        raw = '{"action":"LONG","confidence":0.83,"position_size":0.25,"reasoning":"invalid"}'
        with self.assertRaises(Exception):
            parse_decision_json(raw)

    def test_service_converts_response_to_trading_decision(self) -> None:
        client = FakeOpenAIClient(
            response_text='{"action":"SELL","confidence":0.66,"position_size":0.15,"reasoning":"Weak relative strength."}'
        )
        agent = LLMAgent(client=client)
        decision = agent.analyze(self._snapshot())

        self.assertEqual(decision.symbol, 'AAPL')
        self.assertEqual(decision.action, 'SELL')
        self.assertAlmostEqual(decision.confidence or 0.0, 0.66, places=6)
        self.assertEqual(decision.meta.get('position_size'), 0.15)
        self.assertIn('Weak relative strength', decision.rationale)


if __name__ == '__main__':
    unittest.main()

