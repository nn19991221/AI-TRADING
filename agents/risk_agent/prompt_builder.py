from __future__ import annotations

import json
from typing import Protocol

from core.contracts.market_snapshot import LLMMarketSnapshot


class DecisionLike(Protocol):
    action: str
    confidence: float | None
    qty: int | None
    rationale: str
    meta: dict

    def normalized_action(self) -> str:
        ...


SYSTEM_PROMPT = (
    'You are a pre-trade risk gate agent. '
    'Return strict JSON with keys: approved, reason, adjusted_action, max_position_size. '
    'approved must be boolean. adjusted_action must be BUY|SELL|HOLD. '
    'max_position_size must be float in [0,1]. '
    'Do not include markdown or extra keys.'
)


def build_messages(snapshot: LLMMarketSnapshot, decision: DecisionLike) -> tuple[str, str]:
    payload = {
        'symbol': snapshot.symbol,
        'latest_price': snapshot.latest_price,
        'indicators': snapshot.indicators,
        'decision': {
            'action': decision.normalized_action(),
            'confidence': decision.confidence,
            'qty': decision.qty,
            'rationale': decision.rationale,
            'meta': decision.meta,
        },
    }
    user_prompt = 'Evaluate risk and return strict JSON.\n' + json.dumps(payload, ensure_ascii=True)
    return SYSTEM_PROMPT, user_prompt
