from __future__ import annotations

import math

from core.contracts.market_snapshot import LLMMarketSnapshot, NewsItemContract


DEFAULT_SIGNAL_WEIGHTS: dict[str, float] = {
    'momentum': 0.35,
    'volume_spike': 0.25,
    'news_sentiment': 0.20,
    'volatility_breakout': 0.20,
}


def compute_ranking_signals(snapshot: LLMMarketSnapshot) -> dict[str, float]:
    closes = [bar.close for bar in snapshot.bars]
    volumes = [bar.volume for bar in snapshot.bars]

    return {
        'momentum': momentum_score(closes, lookback=20),
        'volume_spike': volume_spike_score(volumes, window=20),
        'news_sentiment': news_sentiment_score(snapshot.news),
        'volatility_breakout': volatility_breakout_score(closes, window=20),
    }


def weighted_rank_score(signals: dict[str, float], weights: dict[str, float] | None = None) -> float:
    weights = weights or DEFAULT_SIGNAL_WEIGHTS
    total_weight = 0.0
    score = 0.0

    for name, weight in weights.items():
        if weight <= 0:
            continue
        total_weight += weight
        score += signals.get(name, 0.0) * weight

    if total_weight <= 0:
        return 0.0
    return score / total_weight


def momentum_score(closes: list[float], lookback: int = 20) -> float:
    if lookback <= 0 or len(closes) < lookback + 1:
        return 0.0
    start = closes[-(lookback + 1)]
    end = closes[-1]
    if start <= 0:
        return 0.0
    raw = (end - start) / start
    return _clamp(raw, -1.0, 1.0)


def volume_spike_score(volumes: list[int], window: int = 20) -> float:
    if window <= 1 or len(volumes) < window + 1:
        return 0.0
    baseline = volumes[-(window + 1) : -1]
    avg = sum(baseline) / len(baseline)
    if avg <= 0:
        return 0.0
    raw = (volumes[-1] / avg) - 1.0
    return _clamp(raw, -1.0, 1.0)


def news_sentiment_score(news_items: list[NewsItemContract]) -> float:
    if not news_items:
        return 0.0

    scores: list[float] = []
    for item in news_items:
        if item.sentiment is not None:
            scores.append(float(item.sentiment))
            continue
        scores.append(_keyword_sentiment(item.headline, item.summary))

    if not scores:
        return 0.0
    return _clamp(sum(scores) / len(scores), -1.0, 1.0)


def volatility_breakout_score(closes: list[float], window: int = 20) -> float:
    if window <= 1 or len(closes) < window + 1:
        return 0.0

    subset = closes[-(window + 1) :]
    returns: list[float] = []
    for prev, curr in zip(subset[:-1], subset[1:]):
        if prev == 0:
            continue
        returns.append((curr - prev) / prev)

    if len(returns) < 2:
        return 0.0

    mean_r = sum(returns[:-1]) / max(1, len(returns) - 1)
    variance = sum((x - mean_r) ** 2 for x in returns[:-1]) / max(1, len(returns) - 2)
    std_r = math.sqrt(variance) if variance > 0 else 0.0
    if std_r == 0:
        return 0.0

    zscore = abs((returns[-1] - mean_r) / std_r)
    normalized = min(zscore / 3.0, 1.0)
    return normalized


def _keyword_sentiment(headline: str, summary: str) -> float:
    text = f'{headline} {summary}'.lower()
    positives = ['beat', 'surge', 'strong', 'growth', 'upgrade', 'record', 'bullish', 'outperform']
    negatives = ['miss', 'drop', 'weak', 'downgrade', 'lawsuit', 'bearish', 'cut', 'decline']

    pos_hits = sum(1 for token in positives if token in text)
    neg_hits = sum(1 for token in negatives if token in text)
    if pos_hits == 0 and neg_hits == 0:
        return 0.0

    raw = (pos_hits - neg_hits) / (pos_hits + neg_hits)
    return _clamp(raw, -1.0, 1.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

