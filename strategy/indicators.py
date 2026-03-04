from __future__ import annotations


def simple_moving_average(values: list[float], window: int) -> float:
    if window <= 0:
        raise ValueError('window must be positive')
    if len(values) < window:
        raise ValueError('insufficient values for moving average')
    subset = values[-window:]
    return sum(subset) / window
