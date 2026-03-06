from __future__ import annotations

from typing import Any

from core.contracts.market_snapshot import LLMMarketSnapshot


def build_market_summary(snapshot: LLMMarketSnapshot) -> dict[str, Any]:
    closes = [bar.close for bar in snapshot.bars]
    volumes = [bar.volume for bar in snapshot.bars]

    trend = _trend(snapshot, closes)
    volatility = _volatility(snapshot, closes)
    momentum = _momentum(snapshot, closes)
    volume_spike = _volume_spike(volumes)

    return {
        'trend': trend,
        'volatility': volatility,
        'momentum': momentum,
        'volume_spike': volume_spike,
    }


def _trend(snapshot: LLMMarketSnapshot, closes: list[float]) -> str:
    fast = _to_float(snapshot.indicators.get('sma_fast'))
    slow = _to_float(snapshot.indicators.get('sma_slow'))
    if fast is not None and slow is not None:
        if fast > slow:
            return 'uptrend'
        if fast < slow:
            return 'downtrend'
        return 'sideways'

    if len(closes) < 5:
        return 'sideways'
    if closes[-1] > closes[0]:
        return 'uptrend'
    if closes[-1] < closes[0]:
        return 'downtrend'
    return 'sideways'


def _volatility(snapshot: LLMMarketSnapshot, closes: list[float]) -> str:
    vol = _to_float(snapshot.indicators.get('volatility'))
    if vol is None and len(closes) >= 2:
        returns = []
        for prev, curr in zip(closes[:-1], closes[1:]):
            if prev != 0:
                returns.append(abs((curr - prev) / prev))
        vol = sum(returns) / len(returns) if returns else 0.0
    vol = vol or 0.0

    if vol < 0.008:
        return 'low'
    if vol < 0.02:
        return 'medium'
    return 'high'


def _momentum(snapshot: LLMMarketSnapshot, closes: list[float]) -> str:
    ret = _to_float(snapshot.indicators.get('return_1'))
    if ret is None and len(closes) >= 2 and closes[-2] != 0:
        ret = (closes[-1] - closes[-2]) / closes[-2]
    ret = ret or 0.0

    if ret > 0.002:
        return 'positive'
    if ret < -0.002:
        return 'negative'
    return 'neutral'


def _volume_spike(volumes: list[int]) -> bool:
    if len(volumes) < 6:
        return False
    baseline = volumes[:-1]
    avg = sum(baseline) / len(baseline)
    if avg <= 0:
        return False
    return volumes[-1] >= (avg * 1.5)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

