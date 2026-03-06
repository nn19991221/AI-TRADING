from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from metrics.runtime_audit import update_runtime_audit


class RuntimeAuditTest(unittest.TestCase):
    def test_runtime_audit_accumulates_daily_metrics(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            report_path = base / 'runtime_audit.json'
            state_path = base / 'runtime_state.json'
            now = datetime.now(timezone.utc)

            report = update_runtime_audit(
                cycle_time=now,
                total_symbols=5,
                strategy_agent_calls=1,
                strategy_symbols_sent=3,
                frequency_agent_calls=1,
                cache_hits=2,
                trades_executed=1,
                blocked_by_risk_guard=1,
                blocked_by_circuit_breaker=0,
                next_check_minutes=6,
                fallback_used=False,
                strategy_mode='llm',
                report_path=report_path,
                state_path=state_path,
            )

            self.assertEqual(report['total_cycles'], 1)
            self.assertEqual(report['strategy_mode'], 'llm')
            self.assertEqual(report['cache_hit_rate'], 0.4)
            self.assertEqual(report['fallback_usage_rate'], 0.0)
            self.assertGreater(report['estimated_token_usage_per_day'], 0)

            report = update_runtime_audit(
                cycle_time=now,
                total_symbols=5,
                strategy_agent_calls=0,
                strategy_symbols_sent=0,
                frequency_agent_calls=1,
                cache_hits=5,
                trades_executed=0,
                blocked_by_risk_guard=0,
                blocked_by_circuit_breaker=1,
                next_check_minutes=5,
                fallback_used=True,
                strategy_mode='fallback_legacy',
                report_path=report_path,
                state_path=state_path,
            )

            self.assertEqual(report['total_cycles'], 2)
            self.assertEqual(report['strategy_mode'], 'fallback_legacy')
            self.assertEqual(report['strategy_mode_breakdown']['llm_cycles'], 1)
            self.assertEqual(report['strategy_mode_breakdown']['fallback_legacy_cycles'], 1)
            self.assertEqual(report['blocked_trades_by_risk_guard'], 1)
            self.assertEqual(report['blocked_trades_by_circuit_breaker'], 1)
            self.assertEqual(report['average_next_check_minutes'], 5.5)
            self.assertEqual(report['fallback_usage_rate'], 0.5)
            self.assertEqual(report['cache_hit_rate'], 0.7)

            saved = json.loads(report_path.read_text(encoding='utf-8'))
            self.assertEqual(saved['total_cycles'], 2)
            self.assertEqual(saved['strategy_mode'], 'fallback_legacy')


if __name__ == '__main__':
    unittest.main()
