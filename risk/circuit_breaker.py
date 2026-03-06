from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


MAX_CONSECUTIVE_LOSSES = 5
MAX_DRAWDOWN = 0.08
PAUSE_MINUTES = 60


@dataclass
class BreakerStatus:
    paused: bool
    reason: str
    resume_at: datetime | None


class CircuitBreaker:
    def __init__(self):
        self.pause_until: datetime | None = None
        self.consecutive_losses = 0
        self.day_key: str | None = None
        self.day_start_equity: float | None = None
        self.last_daily_pnl: float | None = None

    def is_paused(self, now: datetime | None = None) -> bool:
        current = _to_utc(now or datetime.now(timezone.utc))
        return bool(self.pause_until and current < self.pause_until)

    def status(self, now: datetime | None = None) -> BreakerStatus:
        paused = self.is_paused(now=now)
        if paused:
            return BreakerStatus(True, 'CIRCUIT_BREAKER_PAUSED', self.pause_until)
        return BreakerStatus(False, 'CIRCUIT_BREAKER_OK', self.pause_until)

    def update_after_cycle(
        self,
        *,
        portfolio_state: dict[str, Any],
        trades_executed: int,
        now: datetime | None = None,
    ) -> BreakerStatus:
        current = _to_utc(now or datetime.now(timezone.utc))
        day_key = current.date().isoformat()
        if day_key != self.day_key:
            self.day_key = day_key
            self.day_start_equity = None
            self.last_daily_pnl = None
            self.consecutive_losses = 0

        equity = _to_float(portfolio_state.get('equity', 0.0))
        daily_pnl = _to_float(portfolio_state.get('daily_pnl', 0.0))

        if self.day_start_equity is None and equity > 0:
            self.day_start_equity = equity

        if trades_executed > 0:
            if daily_pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0

        if self.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            self.pause_until = current + timedelta(minutes=PAUSE_MINUTES)
            return BreakerStatus(True, 'CIRCUIT_BREAKER_CONSECUTIVE_LOSSES', self.pause_until)

        if self.day_start_equity and self.day_start_equity > 0 and equity > 0:
            drawdown = (self.day_start_equity - equity) / self.day_start_equity
            if drawdown > MAX_DRAWDOWN:
                self.pause_until = current + timedelta(minutes=PAUSE_MINUTES)
                return BreakerStatus(True, 'CIRCUIT_BREAKER_DRAWDOWN', self.pause_until)

        self.last_daily_pnl = daily_pnl
        return self.status(now=current)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

