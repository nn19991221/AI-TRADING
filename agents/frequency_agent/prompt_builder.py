from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = (
    'You are a trading cycle frequency scheduler. '
    'Return strict JSON with keys: next_check_minutes, reason. '
    'next_check_minutes must be an integer between 1 and 15. '
    'Use these factors when deciding frequency: market volatility, momentum signals, open positions, and recent trade activity. '
    'Do not include markdown or extra keys.'
)


def build_messages(
    results: list[dict[str, Any]],
    portfolio_state: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> tuple[str, str]:
    context = context or {}
    volatility = context.get('avg_market_volatility')
    if volatility is None:
        vol_values = [float(item.get('volatility', 0.0)) for item in results]
        volatility = (sum(vol_values) / len(vol_values)) if vol_values else 0.0

    open_positions = context.get('open_positions')
    if open_positions is None:
        raw_positions = portfolio_state.get('positions', [])
        open_positions = len(raw_positions) if isinstance(raw_positions, list) else 0

    recent_trade_activity = context.get('recent_trade_activity')
    if recent_trade_activity is None:
        recent_trade_activity = sum(
            1
            for item in results
            if str(item.get('execution_status', '')).upper() not in {'', 'SKIPPED_RISK_REJECTED', 'SKIPPED_HOLD'}
        )

    payload = {
        'volatility': volatility,
        'open_positions': int(open_positions),
        'recent_trade_activity': int(recent_trade_activity),
    }
    user_prompt = (
        'Given the runtime activity metrics, recommend the next cycle interval in minutes.\n'
        + json.dumps(payload, ensure_ascii=True, default=str)
    )
    return SYSTEM_PROMPT, user_prompt
