from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from state.portfolio_store import load_portfolio_state, save_portfolio_state


class PortfolioStoreTest(unittest.TestCase):
    def test_save_and_load_portfolio_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'portfolio.json'
            sample = {
                'cash': 1000.0,
                'positions': {'AAPL': 5.0},
                'realized_pnl': 12.5,
                'unrealized_pnl': -3.2,
            }
            save_portfolio_state(sample, file_path=path)
            loaded = load_portfolio_state(file_path=path)
            self.assertEqual(loaded['cash'], 1000.0)
            self.assertEqual(loaded['positions'], {'AAPL': 5.0})
            self.assertEqual(loaded['realized_pnl'], 12.5)
            self.assertEqual(loaded['unrealized_pnl'], -3.2)


if __name__ == '__main__':
    unittest.main()

