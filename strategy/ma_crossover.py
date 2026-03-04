from __future__ import annotations

from dataclasses import dataclass

from strategy.indicators import simple_moving_average


@dataclass
class SignalResult:
    symbol: str
    signal: str
    fast_ma: float
    slow_ma: float


class MovingAverageCrossoverStrategy:
    def __init__(self, fast_window: int, slow_window: int):
        if fast_window >= slow_window:
            raise ValueError('fast window must be smaller than slow window')
        self.fast_window = fast_window
        self.slow_window = slow_window

    def generate_signal(self, symbol: str, closes: list[float]) -> SignalResult:
        min_required = max(self.fast_window, self.slow_window)
        if len(closes) < min_required:
            return SignalResult(symbol=symbol, signal='HOLD', fast_ma=0.0, slow_ma=0.0)

        fast_ma = simple_moving_average(closes, self.fast_window)
        slow_ma = simple_moving_average(closes, self.slow_window)

        if fast_ma > slow_ma:
            signal = 'BUY'
        elif fast_ma < slow_ma:
            signal = 'SELL'
        else:
            signal = 'HOLD'

        return SignalResult(symbol=symbol, signal=signal, fast_ma=fast_ma, slow_ma=slow_ma)
