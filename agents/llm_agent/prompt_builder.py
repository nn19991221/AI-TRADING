from __future__ import annotations

import json

from core.contracts.market_snapshot import LLMMarketSnapshot


SYSTEM_PROMPT = (
    'You are an autonomous equities trading decision agent. '
    'Return ONLY strict JSON with keys: '
    'action, confidence, position_size, reasoning. '
    'Allowed action values: BUY, SELL, HOLD. '
    'confidence must be a float in [0,1]. '
    'position_size must be a float in [0,1]. '
    'Do not include markdown, code fences, or extra keys.'
)


def build_prompt(snapshot: LLMMarketSnapshot, max_bars: int = 40, max_news: int = 8) -> str:
    """
    Build compact market context for LLM inference.
    """
    bars = snapshot.bars[-max_bars:] if max_bars > 0 else []
    news = snapshot.news[:max_news] if max_news > 0 else []

    payload = {
        'symbol': snapshot.symbol,
        'timeframe': snapshot.timeframe,
        'as_of': snapshot.as_of.isoformat(),
        'latest_price': snapshot.latest_price,
        'indicators': snapshot.indicators,
        'bars': [
            {
                'timestamp': bar.timestamp.isoformat(),
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
            }
            for bar in bars
        ],
        'news': [
            {
                'headline': item.headline,
                'summary': item.summary,
                'source': item.source,
                'published_at': item.published_at.isoformat() if item.published_at else None,
                'symbols': item.symbols,
                'sentiment': item.sentiment,
            }
            for item in news
        ],
    }

    return (
        'Analyze the following market snapshot and provide one trade decision.\n'
        'Market snapshot JSON:\n'
        f'{json.dumps(payload, ensure_ascii=True)}'
    )


def build_messages(snapshot: LLMMarketSnapshot) -> tuple[str, str]:
    return SYSTEM_PROMPT, build_prompt(snapshot)

