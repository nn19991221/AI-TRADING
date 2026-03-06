from __future__ import annotations

import argparse
from datetime import datetime, time as dt_time
import logging
import time
from zoneinfo import ZoneInfo

from app.run_trader import build_components, format_report
from broker.alpaca_broker import AlpacaBroker
from config.settings import Settings, get_settings
from orchestrator.trading_cycle import run_cycle

MIN_INTERVAL = 1
MAX_INTERVAL = 15
DEFAULT_INTERVAL = 5


def run_trading_loop(
    *,
    symbols_override: list[str] | None = None,
    top_n: int | None = None,
    max_cycles: int | None = None,
    settings: Settings | None = None,
    sleep_fn=time.sleep,
) -> None:
    settings = settings or get_settings()
    components = build_components(settings=settings)

    cycle_count = 0
    while market_is_open(settings=settings):
        symbols = _resolve_symbols(
            symbols_override=symbols_override,
            top_n=top_n,
            settings=settings,
            components=components,
        )

        try:
            report = run_cycle(
                symbols,
                data_agent=components.data_agent,
                strategy_agent=components.strategy_agent,
                risk_guard=components.risk_guard,
                frequency_agent=components.frequency_agent,
                executor=components.executor,
                portfolio_updater=components.portfolio_updater,
            )
            print(format_report(report))
            interval_minutes = _sanitize_interval(report.next_check_minutes)
        except Exception as exc:
            logging.exception('Trading cycle failed: %s', exc)
            interval_minutes = DEFAULT_INTERVAL

        logging.info('Next cycle in %s minute(s)', interval_minutes)
        sleep_fn(interval_minutes * 60)

        cycle_count += 1
        if max_cycles is not None and cycle_count >= max_cycles:
            break


def market_is_open(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    try:
        broker = AlpacaBroker(settings)
        clock = broker.trading.get_clock()
        return bool(getattr(clock, 'is_open', False))
    except Exception:
        # Fallback market-hours check if broker clock is unavailable.
        now_et = datetime.now(ZoneInfo('America/New_York'))
        if now_et.weekday() >= 5:
            return False
        open_time = dt_time(9, 30)
        close_time = dt_time(16, 0)
        now_time = now_et.time()
        return open_time <= now_time <= close_time


def _resolve_symbols(
    *,
    symbols_override: list[str] | None,
    top_n: int | None,
    settings: Settings,
    components,
) -> list[str]:
    if symbols_override:
        return _normalize_symbols(symbols_override)

    selected = components.stock_selector.select_symbols(top_n=top_n)
    if selected:
        return selected

    return _normalize_symbols(settings.symbol_list)


def _sanitize_interval(next_check_minutes: int | None) -> int:
    try:
        minutes = int(next_check_minutes) if next_check_minutes is not None else DEFAULT_INTERVAL
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL
    if minutes < MIN_INTERVAL or minutes > MAX_INTERVAL:
        return DEFAULT_INTERVAL
    return minutes


def _normalize_symbols(raw: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in raw:
        symbol = value.strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        normalized.append(symbol)
    return normalized


def _parse_symbols(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return _normalize_symbols(raw.split(','))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

    parser = argparse.ArgumentParser(description='Run adaptive trading loop while market is open.')
    parser.add_argument('--symbols', type=str, default='', help='Optional comma-separated symbols override.')
    parser.add_argument('--top-n', type=int, default=None, help='Number of symbols to select each cycle.')
    parser.add_argument('--max-cycles', type=int, default=None, help='Optional safety cap for cycles.')
    args = parser.parse_args()

    run_trading_loop(
        symbols_override=_parse_symbols(args.symbols),
        top_n=args.top_n,
        max_cycles=args.max_cycles,
    )


if __name__ == '__main__':
    main()
