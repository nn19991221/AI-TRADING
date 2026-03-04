from __future__ import annotations

import math

from backtest.models import EquityPoint


def max_drawdown(equity_curve: list[EquityPoint]) -> float:
    peak = float('-inf')
    worst_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point.equity)
        if peak <= 0:
            continue
        drawdown = (peak - point.equity) / peak
        worst_drawdown = max(worst_drawdown, drawdown)
    return worst_drawdown


def sharpe_ratio(equity_curve: list[EquityPoint], bars_per_year: int = 252 * 13) -> float:
    if len(equity_curve) < 2:
        return 0.0

    returns: list[float] = []
    for prev, curr in zip(equity_curve[:-1], equity_curve[1:]):
        if prev.equity <= 0:
            continue
        returns.append((curr.equity - prev.equity) / prev.equity)

    if len(returns) < 2:
        return 0.0

    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance)
    if std_r == 0:
        return 0.0

    return (mean_r / std_r) * math.sqrt(bars_per_year)
