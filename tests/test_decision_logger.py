from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from logs.decision_logger import log_decision


class DecisionLoggerTest(unittest.TestCase):
    def test_log_decision_writes_jsonl_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'decisions.jsonl'
            log_decision(
                {
                    'symbol': 'AAPL',
                    'agent': 'decision',
                    'action': 'BUY',
                    'confidence': 0.82,
                    'reason': 'test',
                    'price': 101.5,
                    'volatility': 0.02,
                    'next_check_minutes': 3,
                },
                file_path=path,
            )
            lines = path.read_text(encoding='utf-8').strip().splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload['symbol'], 'AAPL')
            self.assertEqual(payload['agent'], 'decision')
            self.assertEqual(payload['action'], 'BUY')
            self.assertEqual(payload['next_check_minutes'], 3)
            self.assertIn('timestamp', payload)


if __name__ == '__main__':
    unittest.main()

