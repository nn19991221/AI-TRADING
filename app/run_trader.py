from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timezone
import logging
import os
from typing import Iterable

from agents.data_agent import DataAgent, build_default_data_agent
from agents.decision_agent.service import DecisionAgent, build_default_decision_agent
from agents.frequency_agent.service import FrequencyAgent, build_default_frequency_agent
from agents.market_agent.service import MarketAnalysisAgent, build_default_market_agent
from agents.risk_agent.service import RiskAgent, build_default_risk_agent
from agents.stock_selector.service import StockSelector
from agents.stock_selector.universe import TradingUniverseBuilder
from broker.alpaca_broker import AlpacaBroker
from config.settings import Settings, get_settings
from execution.order_executor import OrderExecutor
from orchestrator.trading_cycle import (
    DefaultPortfolioUpdater,
    DefaultTradingExecutor,
    TradingCycleReport,
    run_cycle,
)
from portfolio.portfolio_manager import PortfolioManager
from risk.risk_manager import RiskManager


@dataclass
class TraderComponents:
    data_agent: DataAgent
    market_agent: MarketAnalysisAgent
    decision_agent: DecisionAgent
    risk_agent: RiskAgent
    frequency_agent: FrequencyAgent
    stock_selector: StockSelector
    executor: DefaultTradingExecutor
    portfolio_updater: DefaultPortfolioUpdater


def build_components(settings: Settings | None = None) -> TraderComponents:
    settings = settings or get_settings()

    data_agent = build_default_data_agent(settings=settings)
    market_agent = build_default_market_agent(model=settings.llm_market_model)
    decision_agent = build_default_decision_agent(model=settings.llm_decision_model)
    risk_agent = build_default_risk_agent(model=settings.llm_risk_model)
    frequency_agent = build_default_frequency_agent(model=settings.llm_scheduler_model)

    selector_top_n = int(os.getenv('SELECTOR_TOP_N', '5'))
    selector_min_bars = int(os.getenv('SELECTOR_MIN_BARS', '25'))
    stock_selector = StockSelector(
        data_agent=data_agent,
        universe_builder=TradingUniverseBuilder(settings=settings),
        top_n=selector_top_n,
        min_bars=selector_min_bars,
    )

    broker = AlpacaBroker(settings)
    base_risk_manager = RiskManager(
        max_position_pct=settings.max_position_pct,
        max_daily_drawdown_pct=settings.max_daily_drawdown_pct,
    )

    order_executor = OrderExecutor(broker=broker, risk_manager=base_risk_manager)
    executor = DefaultTradingExecutor(order_executor=order_executor)

    portfolio_manager = PortfolioManager(broker=broker)
    portfolio_updater = DefaultPortfolioUpdater(portfolio_manager=portfolio_manager)

    return TraderComponents(
        data_agent=data_agent,
        market_agent=market_agent,
        decision_agent=decision_agent,
        risk_agent=risk_agent,
        frequency_agent=frequency_agent,
        stock_selector=stock_selector,
        executor=executor,
        portfolio_updater=portfolio_updater,
    )


def run_trader(
    symbols_override: list[str] | None = None,
    top_n: int | None = None,
    settings: Settings | None = None,
) -> TradingCycleReport:
    settings = settings or get_settings()
    components = build_components(settings=settings)

    symbols = _resolve_symbols(
        symbols_override=symbols_override,
        stock_selector=components.stock_selector,
        top_n=top_n,
        default_symbols=settings.symbol_list,
    )

    return run_cycle(
        symbols,
        data_agent=components.data_agent,
        market_agent=components.market_agent,
        decision_agent=components.decision_agent,
        risk_agent=components.risk_agent,
        frequency_agent=components.frequency_agent,
        executor=components.executor,
        portfolio_updater=components.portfolio_updater,
    )


def format_report(report: TradingCycleReport) -> str:
    lines: list[str] = []
    started = report.started_at.astimezone(timezone.utc).isoformat()
    finished = report.finished_at.astimezone(timezone.utc).isoformat()
    duration_seconds = max(0.0, (report.finished_at - report.started_at).total_seconds())

    lines.append('=== AI Trading Cycle Report ===')
    lines.append(f'Started (UTC):  {started}')
    lines.append(f'Finished (UTC): {finished}')
    lines.append(f'Duration:       {duration_seconds:.2f}s')
    if report.next_check_minutes is not None:
        lines.append(f'Next Check:     {report.next_check_minutes} minutes')
    if report.frequency_reason:
        lines.append(f'Schedule Note:  {report.frequency_reason}')
    lines.append('')
    lines.append('Per-Symbol Results:')
    lines.append('symbol | decision | approved | risk_reason          | execution_status')
    lines.append('-------+----------+----------+----------------------+-----------------------')

    if not report.results:
        lines.append('(no symbols processed)')
    else:
        for result in report.results:
            lines.append(
                f'{result.symbol:<6} | {result.decision:<8} | {str(result.approved):<8} | '
                f'{result.risk_reason:<20} | {result.execution_status}'
            )

    lines.append('')
    lines.append('Portfolio:')
    if not report.portfolio_state:
        lines.append('(no portfolio state)')
    else:
        for key in sorted(report.portfolio_state.keys()):
            lines.append(f'- {key}: {report.portfolio_state[key]}')

    return '\n'.join(lines)


def main() -> None:
    _configure_logging()

    parser = argparse.ArgumentParser(description='Run one autonomous AI trading cycle.')
    parser.add_argument(
        '--symbols',
        type=str,
        default='',
        help='Optional comma-separated symbols override, e.g. AAPL,MSFT',
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=None,
        help='Number of symbols to select when not using --symbols.',
    )
    args = parser.parse_args()

    symbols_override = _parse_symbols_arg(args.symbols)
    report = run_trader(symbols_override=symbols_override, top_n=args.top_n)
    print(format_report(report))


def _resolve_symbols(
    symbols_override: list[str] | None,
    stock_selector: StockSelector,
    top_n: int | None,
    default_symbols: list[str],
) -> list[str]:
    if symbols_override:
        return _normalize_symbols(symbols_override)

    selected = stock_selector.select_symbols(top_n=top_n)
    if selected:
        return selected

    return _normalize_symbols(default_symbols)


def _parse_symbols_arg(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return _normalize_symbols(raw.split(','))


def _normalize_symbols(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        symbol = value.strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        output.append(symbol)
    return output


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )


if __name__ == '__main__':
    main()
