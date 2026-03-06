from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from app.run_trader import _resolve_symbols, format_report
from orchestrator.trading_cycle import TradingCycleReport, TradingSymbolResult


class FakeSelector:
    def __init__(self, symbols: list[str]):
        self.symbols = symbols

    def select_symbols(self, top_n=None):
        if top_n is None:
            return self.symbols
        return self.symbols[:top_n]


class RunTraderTest(unittest.TestCase):
    def test_resolve_symbols_prefers_override(self) -> None:
        symbols = _resolve_symbols(
            symbols_override=['aapl', 'msft'],
            stock_selector=FakeSelector(['TSLA']),
            top_n=None,
            default_symbols=['SPY'],
        )
        self.assertEqual(symbols, ['AAPL', 'MSFT'])

    def test_resolve_symbols_falls_back_to_defaults(self) -> None:
        symbols = _resolve_symbols(
            symbols_override=[],
            stock_selector=FakeSelector([]),
            top_n=3,
            default_symbols=['QQQ', 'IWM'],
        )
        self.assertEqual(symbols, ['QQQ', 'IWM'])

    def test_format_report_contains_core_sections(self) -> None:
        start = datetime.now(timezone.utc)
        report = TradingCycleReport(
            started_at=start,
            finished_at=start + timedelta(seconds=2),
            results=[
                TradingSymbolResult(
                    symbol='AAPL',
                    decision='BUY',
                    approved=True,
                    risk_reason='APPROVED',
                    execution_status='accepted',
                    latest_price=100.0,
                    as_of=start,
                )
            ],
            portfolio_state={'equity': 100_000.0},
        )
        output = format_report(report)
        self.assertIn('AI Trading Cycle Report', output)
        self.assertIn('Per-Symbol Results', output)
        self.assertIn('Portfolio', output)
        self.assertIn('AAPL', output)


if __name__ == '__main__':
    unittest.main()

