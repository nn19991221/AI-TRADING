from __future__ import annotations

import json

from core.contracts.market_snapshot import LLMMarketSnapshot


SYSTEM_PROMPT = (
    'You are a market analysis agent for US equities. '
    'Return strict JSON with keys: trend, momentum, volatility_regime, news_sentiment, summary. '
    'trend must be BULLISH|BEARISH|NEUTRAL. '
    'momentum and news_sentiment must be floats in [-1,1]. '
    'volatility_regime must be LOW|MEDIUM|HIGH. '
    'Do not include markdown or extra keys.'
)


def build_messages(snapshot: LLMMarketSnapshot) -> tuple[str, str]:
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
            for bar in snapshot.bars[-40:]
        ],
        'news': [
            {
                'headline': item.headline,
                'summary': item.summary,
                'source': item.source,
                'sentiment': item.sentiment,
                'published_at': item.published_at.isoformat() if item.published_at else None,
            }
            for item in snapshot.news[:10]
        ],
    }
    user_prompt = 'Analyze market regime and return JSON.\n' + json.dumps(payload, ensure_ascii=True)
    return SYSTEM_PROMPT, user_prompt

