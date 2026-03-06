from __future__ import annotations

import math

from strategy.indicators import simple_moving_average


def compute_indicators(
    closes: list[float],
    fast_window: int = 5,
    slow_window: int = 20,
    rsi_window: int = 14,
    volatility_window: int = 20,
) -> dict[str, float]:
    """
    Returns a compact numeric feature set suitable for LLM context.
    Missing indicators are omitted instead of returning NaN.
    """
    if not closes:
        return {}

    features: dict[str, float] = {'close': float(closes[-1])}

    if len(closes) >= 2 and closes[-2] != 0:
        features['return_1'] = (closes[-1] - closes[-2]) / closes[-2]

    if len(closes) >= fast_window:
        features['sma_fast'] = simple_moving_average(closes, fast_window)

    if len(closes) >= slow_window:
        features['sma_slow'] = simple_moving_average(closes, slow_window)

    ema_fast = _ema(closes, fast_window)
    if ema_fast is not None:
        features['ema_fast'] = ema_fast

    ema_slow = _ema(closes, slow_window)
    if ema_slow is not None:
        features['ema_slow'] = ema_slow

    rsi_value = _rsi(closes, rsi_window)
    if rsi_value is not None:
        features['rsi'] = rsi_value

    volatility = _rolling_return_std(closes, volatility_window)
    if volatility is not None:
        features['volatility'] = volatility

    return features


def _ema(values: list[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    alpha = 2.0 / (window + 1.0)
    ema = values[0]
    for value in values[1:]:
        ema = alpha * value + (1 - alpha) * ema
    return float(ema)


def _rsi(closes: list[float], window: int) -> float | None:
    if window <= 0 or len(closes) <= window:
        return None

    gains: list[float] = []
    losses: list[float] = []
    for prev, curr in zip(closes[:-1], closes[1:]):
        delta = curr - prev
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window

    for i in range(window, len(gains)):
        avg_gain = ((avg_gain * (window - 1)) + gains[i]) / window
        avg_loss = ((avg_loss * (window - 1)) + losses[i]) / window

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _rolling_return_std(closes: list[float], window: int) -> float | None:
    if window <= 1 or len(closes) < window + 1:
        return None

    subset = closes[-(window + 1) :]
    returns: list[float] = []
    for prev, curr in zip(subset[:-1], subset[1:]):
        if prev == 0:
            continue
        returns.append((curr - prev) / prev)

    if len(returns) < 2:
        return None

    mean_return = sum(returns) / len(returns)
    variance = sum((value - mean_return) ** 2 for value in returns) / (len(returns) - 1)
    return math.sqrt(variance)

