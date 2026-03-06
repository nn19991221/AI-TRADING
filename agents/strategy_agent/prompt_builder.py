from __future__ import annotations

import json

from core.contracts.market_snapshot import LLMMarketSnapshot


SYSTEM_PROMPT = (
    'You are a strategy agent for US equities trading. '
    'Return strict JSON with key "decisions" containing a list of objects. '
    'Each object must include: symbol, market_state, action, confidence, position_size, reason. '
    'Allowed action: BUY|SELL|HOLD. '
    'confidence and position_size in [0,1]. '
    'market_state is a short label like trending_up, trending_down, or rangebound. '
    'Do not include markdown or additional keys.'
)


def build_messages(compact_rows: list[dict]) -> tuple[str, str]:
    payload = {'symbols': compact_rows}
    user_prompt = (
        'Analyze each symbol and produce one decision per symbol.\n'
        + json.dumps(payload, ensure_ascii=True, default=str)
    )
    return SYSTEM_PROMPT, user_prompt


def compact_snapshot_payload(
    snapshot: LLMMarketSnapshot,
    summary: dict,
) -> dict:
    return {
        'symbol': snapshot.symbol,
        'latest_price': snapshot.latest_price,
        'summary': summary,
        'indicators': {
            'sma_fast': snapshot.indicators.get('sma_fast'),
            'sma_slow': snapshot.indicators.get('sma_slow'),
            'return_1': snapshot.indicators.get('return_1'),
            'rsi': snapshot.indicators.get('rsi'),
        },
        'news': [
            {'headline': item.headline, 'summary': item.summary}
            for item in snapshot.news[:3]
        ],
    }

