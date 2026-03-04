from __future__ import annotations

import json

from backtest.data_source import HistoricalBarRepository
from backtest.engine import BacktestEngine
from config.settings import get_settings
from risk.risk_manager import RiskManager
from strategy.ma_crossover import MovingAverageCrossoverStrategy


def main() -> None:
    settings = get_settings()
    strategy = MovingAverageCrossoverStrategy(
        fast_window=settings.fast_ma_window,
        slow_window=settings.slow_ma_window,
    )
    risk_manager = RiskManager(
        max_position_pct=settings.max_position_pct,
        max_daily_drawdown_pct=settings.max_daily_drawdown_pct,
    )
    bars_by_symbol = HistoricalBarRepository().load(settings.symbol_list)

    engine = BacktestEngine(strategy=strategy, risk_manager=risk_manager)
    report = engine.run(bars_by_symbol)

    payload = {
        'equity_curve': [
            {
                'timestamp': point.timestamp.isoformat(),
                'equity': point.equity,
                'cash': point.cash,
            }
            for point in report.equity_curve
        ],
        'max_drawdown': report.max_drawdown,
        'sharpe_ratio': report.sharpe_ratio,
        'trade_log': [trade.__dict__ for trade in report.trade_log],
    }

    print(json.dumps(payload, indent=2, default=str))


if __name__ == '__main__':
    main()
