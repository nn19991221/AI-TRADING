from __future__ import annotations

import logging
from pathlib import Path

from broker.alpaca_broker import AlpacaBroker
from config.settings import get_settings
from data.market_data import MarketDataService
from data.storage import init_db
from execution.order_executor import OrderExecutor
from portfolio.portfolio_manager import PortfolioManager
from risk.risk_manager import RiskManager
from scheduler.job_scheduler import TradingJobScheduler
from strategy.ma_crossover import MovingAverageCrossoverStrategy


def configure_logging() -> None:
    Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[
            logging.FileHandler('logs/trading.log'),
            logging.StreamHandler(),
        ],
    )


def build_app() -> TradingJobScheduler:
    settings = get_settings()

    broker = AlpacaBroker(settings)
    market_data = MarketDataService(broker)
    strategy = MovingAverageCrossoverStrategy(
        fast_window=settings.fast_ma_window,
        slow_window=settings.slow_ma_window,
    )
    risk_manager = RiskManager(
        max_position_pct=settings.max_position_pct,
        max_daily_drawdown_pct=settings.max_daily_drawdown_pct,
    )
    executor = OrderExecutor(broker, risk_manager)
    portfolio = PortfolioManager(broker)

    return TradingJobScheduler(
        settings=settings,
        market_data=market_data,
        strategy=strategy,
        executor=executor,
        portfolio=portfolio,
    )


if __name__ == '__main__':
    configure_logging()
    init_db()
    scheduler = build_app()
    scheduler.run_cycle()
    scheduler.start()
