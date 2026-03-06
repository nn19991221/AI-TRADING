from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


DEFAULT_DAILY_REPORT_PATH = Path('reports/daily_report.json')
DEFAULT_METRICS_STATE_PATH = Path('reports/.daily_metrics_state.json')


def update_daily_metrics(
    *,
    cycle_time: datetime,
    cycle_results: list[dict[str, Any]],
    portfolio_state: dict[str, Any],
    report_path: str | Path = DEFAULT_DAILY_REPORT_PATH,
    state_path: str | Path = DEFAULT_METRICS_STATE_PATH,
) -> dict[str, Any]:
    state = _load_state(state_path)
    cycle_date = _to_utc(cycle_time).date().isoformat()
    if state.get('date') != cycle_date:
        state = _new_state(cycle_date)

    executed = sum(1 for row in cycle_results if str(row.get('execution_status', '')).upper() not in {'', 'SKIPPED_RISK_REJECTED', 'SKIPPED_HOLD'})
    state['total_trades'] += executed

    equity = _to_float(portfolio_state.get('equity', state['last_equity']))
    if state['starting_equity'] == 0 and equity > 0:
        state['starting_equity'] = equity
    pnl_delta = equity - state['last_equity'] if state['last_equity'] > 0 else 0.0
    state['last_equity'] = equity
    state['cumulative_pnl'] += pnl_delta

    if executed > 0:
        if pnl_delta >= 0:
            state['wins'] += executed
        else:
            state['losses'] += executed

    if equity > state['equity_peak']:
        state['equity_peak'] = equity
    if state['equity_peak'] > 0:
        drawdown = (state['equity_peak'] - equity) / state['equity_peak']
        state['max_drawdown'] = max(state['max_drawdown'], drawdown)

    _update_holding_time(state, portfolio_state, _to_utc(cycle_time))

    total_closed = int(state['holding_events'])
    avg_hold = (state['holding_minutes_total'] / total_closed) if total_closed > 0 else 0.0
    total_decisions = state['wins'] + state['losses']
    win_rate = (state['wins'] / total_decisions) if total_decisions > 0 else 0.0

    report = {
        'date': cycle_date,
        'total_trades': int(state['total_trades']),
        'win_rate': win_rate,
        'cumulative_pnl': state['cumulative_pnl'],
        'max_drawdown': state['max_drawdown'],
        'average_holding_time': avg_hold,
    }

    _write_json(report_path, report)
    _write_json(state_path, state)
    return report


def _new_state(date_str: str) -> dict[str, Any]:
    return {
        'date': date_str,
        'total_trades': 0,
        'wins': 0,
        'losses': 0,
        'cumulative_pnl': 0.0,
        'max_drawdown': 0.0,
        'equity_peak': 0.0,
        'starting_equity': 0.0,
        'last_equity': 0.0,
        'open_positions': {},
        'holding_minutes_total': 0.0,
        'holding_events': 0,
    }


def _load_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        return _new_state(datetime.now(timezone.utc).date().isoformat())
    try:
        payload = json.loads(state_path.read_text(encoding='utf-8'))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return _new_state(datetime.now(timezone.utc).date().isoformat())


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str), encoding='utf-8')


def _update_holding_time(state: dict[str, Any], portfolio_state: dict[str, Any], cycle_time: datetime) -> None:
    current_positions: dict[str, float] = {}
    raw_positions = portfolio_state.get('positions', [])
    if isinstance(raw_positions, list):
        for row in raw_positions:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get('symbol', '')).upper()
            qty = _to_float(row.get('qty', 0.0))
            if symbol and qty > 0:
                current_positions[symbol] = qty

    open_positions = state.get('open_positions', {}) if isinstance(state.get('open_positions', {}), dict) else {}

    for symbol, qty in current_positions.items():
        if symbol not in open_positions:
            open_positions[symbol] = {'qty': qty, 'opened_at': cycle_time.isoformat()}
        else:
            open_positions[symbol]['qty'] = qty

    closed_symbols = [symbol for symbol in list(open_positions.keys()) if symbol not in current_positions]
    for symbol in closed_symbols:
        opened_raw = open_positions[symbol].get('opened_at')
        try:
            opened_at = datetime.fromisoformat(str(opened_raw))
            minutes = max(0.0, (_to_utc(cycle_time) - _to_utc(opened_at)).total_seconds() / 60.0)
            state['holding_minutes_total'] += minutes
            state['holding_events'] += 1
        except Exception:
            pass
        del open_positions[symbol]

    state['open_positions'] = open_positions


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

