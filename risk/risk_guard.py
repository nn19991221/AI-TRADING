from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from risk.circuit_breaker import CircuitBreaker


MAX_POSITION_SIZE = 0.2
MAX_TRADES_PER_HOUR = 20
MAX_DAILY_LOSS = 0.1


@dataclass
class RiskGuardResult:
    approved: bool
    action: str
    reason: str


class RiskGuard:
    def __init__(self, circuit_breaker: CircuitBreaker | None = None):
        self.trade_timestamps: deque[datetime] = deque()
        self.day_key: str | None = None
        self.day_start_equity: float | None = None
        self.current_equity: float | None = None
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def validate(
        self,
        decision: Any,
        *,
        portfolio_state: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> RiskGuardResult:
        current = _to_utc(now or datetime.now(timezone.utc))
        self._prune(current)

        if portfolio_state:
            self.update_portfolio(portfolio_state, now=current)

        if self.circuit_breaker.is_paused(now=current):
            return RiskGuardResult(False, 'HOLD', 'CIRCUIT_BREAKER_PAUSED')

        action = str(getattr(decision, 'action', 'HOLD')).upper()
        if action not in {'BUY', 'SELL', 'HOLD'}:
            return RiskGuardResult(False, 'HOLD', 'INVALID_ACTION')

        if action == 'HOLD':
            return RiskGuardResult(False, 'HOLD', 'HOLD_SIGNAL')

        position_size = _to_float(getattr(decision, 'meta', {}).get('position_size', 0.0))
        if position_size > MAX_POSITION_SIZE:
            return RiskGuardResult(False, 'HOLD', 'MAX_POSITION_SIZE_EXCEEDED')

        if len(self.trade_timestamps) >= MAX_TRADES_PER_HOUR:
            return RiskGuardResult(False, 'HOLD', 'MAX_TRADES_PER_HOUR_EXCEEDED')

        if self.day_start_equity and self.current_equity is not None and self.day_start_equity > 0:
            daily_loss = (self.day_start_equity - self.current_equity) / self.day_start_equity
            if daily_loss > MAX_DAILY_LOSS:
                return RiskGuardResult(False, 'HOLD', 'MAX_DAILY_LOSS_EXCEEDED')

        return RiskGuardResult(True, action, 'APPROVED')

    def record_trade(self, now: datetime | None = None) -> None:
        current = _to_utc(now or datetime.now(timezone.utc))
        self._prune(current)
        self.trade_timestamps.append(current)

    def update_portfolio(self, portfolio_state: dict[str, Any], now: datetime | None = None) -> None:
        current = _to_utc(now or datetime.now(timezone.utc))
        day_key = current.date().isoformat()
        if day_key != self.day_key:
            self.day_key = day_key
            self.day_start_equity = None
            self.trade_timestamps.clear()

        equity = _to_float(portfolio_state.get('equity', 0.0))
        if self.day_start_equity is None and equity > 0:
            self.day_start_equity = equity
        if equity > 0:
            self.current_equity = equity

    def update_after_cycle(self, portfolio_state: dict[str, Any], trades_executed: int, now: datetime | None = None) -> None:
        current = _to_utc(now or datetime.now(timezone.utc))
        self.update_portfolio(portfolio_state, now=current)
        self.circuit_breaker.update_after_cycle(
            portfolio_state=portfolio_state,
            trades_executed=trades_executed,
            now=current,
        )

    def _prune(self, current: datetime) -> None:
        cutoff = current - timedelta(hours=1)
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

