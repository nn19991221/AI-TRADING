from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


MAX_TRADES_PER_HOUR = 20
MAX_POSITION_SIZE = 0.2
MAX_DAILY_LOSS = 0.1


@dataclass
class GuardDecision:
    allowed: bool
    reason: str


class SystemGuard:
    def __init__(self):
        self.trade_timestamps: deque[datetime] = deque()
        self.day_key: str | None = None
        self.day_start_equity: float | None = None
        self.current_equity: float | None = None

    def pre_trade_check(self, decision: Any, now: datetime | None = None) -> GuardDecision:
        current_time = _to_utc(now or datetime.now(timezone.utc))
        self._prune_trade_window(current_time)

        if len(self.trade_timestamps) >= MAX_TRADES_PER_HOUR:
            return GuardDecision(False, 'SYSTEM_GUARD_MAX_TRADES_PER_HOUR')

        position_size = _to_float(getattr(decision, 'meta', {}).get('position_size', 0.0))
        if position_size > MAX_POSITION_SIZE:
            return GuardDecision(False, 'SYSTEM_GUARD_MAX_POSITION_SIZE')

        if self.day_start_equity and self.current_equity is not None and self.day_start_equity > 0:
            daily_loss = (self.day_start_equity - self.current_equity) / self.day_start_equity
            if daily_loss > MAX_DAILY_LOSS:
                return GuardDecision(False, 'SYSTEM_GUARD_MAX_DAILY_LOSS')

        return GuardDecision(True, 'SYSTEM_GUARD_OK')

    def record_trade(self, now: datetime | None = None) -> None:
        current_time = _to_utc(now or datetime.now(timezone.utc))
        self._prune_trade_window(current_time)
        self.trade_timestamps.append(current_time)

    def update_portfolio(self, portfolio_state: dict[str, Any], now: datetime | None = None) -> None:
        current_time = _to_utc(now or datetime.now(timezone.utc))
        day_key = current_time.date().isoformat()
        if day_key != self.day_key:
            self.day_key = day_key
            self.day_start_equity = None
            self.trade_timestamps.clear()

        equity = _to_float(portfolio_state.get('equity', 0.0))
        if self.day_start_equity is None and equity > 0:
            self.day_start_equity = equity
        if equity > 0:
            self.current_equity = equity

    def _prune_trade_window(self, now: datetime) -> None:
        cutoff = now - timedelta(hours=1)
        while self.trade_timestamps and self.trade_timestamps[0] < cutoff:
            self.trade_timestamps.popleft()


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

