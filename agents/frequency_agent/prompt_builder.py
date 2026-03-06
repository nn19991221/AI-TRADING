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
    payload = {
        'results': results,
        'portfolio_state': portfolio_state,
        'context': context or {},
    }
    user_prompt = (
        'Given the last cycle outcomes, recommend the next cycle interval in minutes.\n'
        + json.dumps(payload, ensure_ascii=True, default=str)
    )
    return SYSTEM_PROMPT, user_prompt
