from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


DEFAULT_AUDIT_REPORT_PATH = Path('reports/runtime_audit.json')
DEFAULT_AUDIT_STATE_PATH = Path('reports/.runtime_audit_state.json')

# Coarse token-cost estimates for compressed prompts.
ESTIMATED_STRATEGY_TOKENS_PER_CALL_BASE = 500
ESTIMATED_STRATEGY_TOKENS_PER_SYMBOL = 180
ESTIMATED_FREQUENCY_TOKENS_PER_CALL = 120


def update_runtime_audit(
    *,
    cycle_time: datetime,
    total_symbols: int,
    strategy_agent_calls: int,
    strategy_symbols_sent: int,
    frequency_agent_calls: int,
    cache_hits: int,
    trades_executed: int,
    blocked_by_risk_guard: int,
    blocked_by_circuit_breaker: int,
    next_check_minutes: int,
    fallback_used: bool,
    strategy_mode: str,
    report_path: str | Path = DEFAULT_AUDIT_REPORT_PATH,
    state_path: str | Path = DEFAULT_AUDIT_STATE_PATH,
) -> dict[str, Any]:
    state = _load_state(state_path)
    cycle_date = _to_utc(cycle_time).date().isoformat()
    if state.get('date') != cycle_date:
        state = _new_state(cycle_date)

    state['total_cycles'] += 1
    state['strategy_agent_calls'] += max(0, int(strategy_agent_calls))
    state['frequency_agent_calls'] += max(0, int(frequency_agent_calls))
    state['cache_hits'] += max(0, int(cache_hits))
    state['cache_total'] += max(0, int(total_symbols))
    state['total_trades'] += max(0, int(trades_executed))
    state['blocked_trades_risk_guard'] += max(0, int(blocked_by_risk_guard))
    state['blocked_trades_circuit_breaker'] += max(0, int(blocked_by_circuit_breaker))
    state['next_check_total'] += max(0, int(next_check_minutes))
    if fallback_used:
        state['fallback_count'] += 1

    mode = (strategy_mode or '').strip().lower()
    if mode == 'llm':
        state['strategy_mode_llm_cycles'] += 1
    else:
        state['strategy_mode_legacy_cycles'] += 1
    state['strategy_mode_current'] = mode or 'fallback_legacy'

    strategy_tokens = 0
    if strategy_agent_calls > 0:
        strategy_tokens = (ESTIMATED_STRATEGY_TOKENS_PER_CALL_BASE + (ESTIMATED_STRATEGY_TOKENS_PER_SYMBOL * max(0, int(strategy_symbols_sent)))) * max(0, int(strategy_agent_calls))
    frequency_tokens = ESTIMATED_FREQUENCY_TOKENS_PER_CALL * max(0, int(frequency_agent_calls))
    state['estimated_tokens'] += strategy_tokens + frequency_tokens

    total_cycles = max(1, int(state['total_cycles']))
    cache_total = max(1, int(state['cache_total']))
    report = {
        'date': cycle_date,
        'total_cycles': int(state['total_cycles']),
        'strategy_agent_calls': int(state['strategy_agent_calls']),
        'frequency_agent_calls': int(state['frequency_agent_calls']),
        'cache_hit_rate': state['cache_hits'] / cache_total,
        'total_trades': int(state['total_trades']),
        'blocked_trades_by_risk_guard': int(state['blocked_trades_risk_guard']),
        'blocked_trades_by_circuit_breaker': int(state['blocked_trades_circuit_breaker']),
        'average_next_check_minutes': state['next_check_total'] / total_cycles,
        'fallback_usage_rate': state['fallback_count'] / total_cycles,
        'estimated_token_usage_per_day': int(state['estimated_tokens']),
        'strategy_mode': state['strategy_mode_current'],
        'strategy_mode_breakdown': {
            'llm_cycles': int(state['strategy_mode_llm_cycles']),
            'fallback_legacy_cycles': int(state['strategy_mode_legacy_cycles']),
        },
    }

    _write_json(state_path, state)
    _write_json(report_path, report)
    return report


def _new_state(date_str: str) -> dict[str, Any]:
    return {
        'date': date_str,
        'total_cycles': 0,
        'strategy_agent_calls': 0,
        'frequency_agent_calls': 0,
        'cache_hits': 0,
        'cache_total': 0,
        'total_trades': 0,
        'blocked_trades_risk_guard': 0,
        'blocked_trades_circuit_breaker': 0,
        'next_check_total': 0,
        'fallback_count': 0,
        'estimated_tokens': 0,
        'strategy_mode_current': 'fallback_legacy',
        'strategy_mode_llm_cycles': 0,
        'strategy_mode_legacy_cycles': 0,
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


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)

