from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import Settings
from data.market_data import MarketDataService
from data.storage import SignalLog, get_session
from execution.order_executor import OrderExecutor
from portfolio.portfolio_manager import PortfolioManager
from strategy.ma_crossover import MovingAverageCrossoverStrategy


class TradingJobScheduler:
    def __init__(
        self,
        settings: Settings,
        market_data: MarketDataService,
        strategy: MovingAverageCrossoverStrategy,
        executor: OrderExecutor,
        portfolio: PortfolioManager,
    ):
        self.settings = settings
        self.market_data = market_data
        self.strategy = strategy
        self.executor = executor
        self.portfolio = portfolio
        self.scheduler = BlockingScheduler(timezone=settings.scheduler_timezone)
        self.logger = logging.getLogger('trading_scheduler')

    def run_cycle(self) -> None:
        self.logger.info('Starting trading cycle')
        for symbol in self.settings.symbol_list:
            inserted = self.market_data.sync_symbol(symbol)
            closes = self.market_data.load_recent_closes(symbol)
            signal_result = self.strategy.generate_signal(symbol=symbol, closes=closes)

            with get_session() as session:
                session.add(
                    SignalLog(
                        symbol=symbol,
                        timestamp=datetime.utcnow(),
                        signal=signal_result.signal,
                        fast_ma=signal_result.fast_ma,
                        slow_ma=signal_result.slow_ma,
                    )
                )

            latest_price = closes[-1] if closes else 0.0
            status = self.executor.execute_signal(symbol, signal_result.signal, latest_price)
            self.logger.info(
                'Symbol=%s bars_inserted=%s signal=%s order_status=%s',
                symbol,
                inserted,
                signal_result.signal,
                status,
            )

        snapshot = self.portfolio.snapshot()
        self.logger.info('Portfolio snapshot: %s', snapshot)

    def start(self) -> None:
        self.scheduler.add_job(
            self.run_cycle,
            trigger=CronTrigger(minute='*/30'),
            id='trading-cycle',
            replace_existing=True,
        )
        self.logger.info('Scheduler started. Running every 30 minutes.')
        self.scheduler.start()
