from __future__ import annotations

import json

from agents.market_agent.service import MarketAnalysis
from core.contracts.market_snapshot import LLMMarketSnapshot


SYSTEM_PROMPT = (
    'You are a trade decision agent. '
    'Return strict JSON with keys: action, confidence, position_size, reasoning. '
    'action must be BUY|SELL|HOLD. confidence and position_size must be floats in [0,1]. '
    'Do not include markdown or extra keys.'
)


def build_messages(snapshot: LLMMarketSnapshot, market_analysis: MarketAnalysis) -> tuple[str, str]:
    payload = {
        'symbol': snapshot.symbol,
        'timeframe': snapshot.timeframe,
        'latest_price': snapshot.latest_price,
        'indicators': snapshot.indicators,
        'market_analysis': {
            'trend': market_analysis.trend,
            'momentum': market_analysis.momentum,
            'volatility_regime': market_analysis.volatility_regime,
            'news_sentiment': market_analysis.news_sentiment,
            'summary': market_analysis.summary,
        },
    }
    user_prompt = 'Generate one trade decision as strict JSON.\n' + json.dumps(payload, ensure_ascii=True)
    return SYSTEM_PROMPT, user_prompt

