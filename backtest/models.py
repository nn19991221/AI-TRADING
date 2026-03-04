from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Bar:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class SimulatedOrder:
    symbol: str
    side: str
    qty: int
    submitted_at: datetime


@dataclass
class SimulatedTrade:
    symbol: str
    side: str
    qty: int
    fill_price: float
    submitted_at: datetime
    filled_at: datetime


@dataclass
class Position:
    symbol: str
    qty: int = 0
    avg_price: float = 0.0


@dataclass
class EquityPoint:
    timestamp: datetime
    equity: float
    cash: float


@dataclass
class BacktestReport:
    equity_curve: list[EquityPoint] = field(default_factory=list)
    trade_log: list[SimulatedTrade] = field(default_factory=list)
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
