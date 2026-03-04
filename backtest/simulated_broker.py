from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backtest.models import Position, SimulatedOrder, SimulatedTrade


@dataclass
class SimulatedAccount:
    cash: float
    equity: float
    last_equity: float


class SimulatedBroker:
    """Broker simulator with delayed fills: market orders fill on the next bar open."""

    def __init__(self, initial_cash: float):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.pending_orders: list[SimulatedOrder] = []
        self.filled_trades: list[SimulatedTrade] = []
        self._latest_equity = initial_cash

    def place_market_order(self, symbol: str, qty: int, side: str, submitted_at: datetime) -> SimulatedOrder:
        order = SimulatedOrder(symbol=symbol, qty=qty, side=side.upper(), submitted_at=submitted_at)
        self.pending_orders.append(order)
        return order

    def list_open_orders(self) -> list[SimulatedOrder]:
        return list(self.pending_orders)

    def fill_orders_for_open(self, symbol: str, ts: datetime, open_price: float) -> list[SimulatedTrade]:
        trades: list[SimulatedTrade] = []
        still_open: list[SimulatedOrder] = []

        for order in self.pending_orders:
            if order.symbol != symbol or order.submitted_at >= ts:
                still_open.append(order)
                continue

            if order.side == 'BUY':
                notional = open_price * order.qty
                if self.cash < notional:
                    continue
                self.cash -= notional
                self._increase_position(symbol, order.qty, open_price)
            else:
                held_qty = self.positions.get(symbol, Position(symbol=symbol)).qty
                fill_qty = min(order.qty, held_qty)
                if fill_qty <= 0:
                    continue
                self.cash += open_price * fill_qty
                self._decrease_position(symbol, fill_qty)
                order.qty = fill_qty

            trade = SimulatedTrade(
                symbol=symbol,
                side=order.side,
                qty=order.qty,
                fill_price=open_price,
                submitted_at=order.submitted_at,
                filled_at=ts,
            )
            self.filled_trades.append(trade)
            trades.append(trade)

        self.pending_orders = still_open
        return trades

    def get_account(self) -> SimulatedAccount:
        return SimulatedAccount(cash=self.cash, equity=self._latest_equity, last_equity=self.initial_cash)

    def mark_to_market(self, close_prices: dict[str, float]) -> float:
        market_value = 0.0
        for symbol, position in self.positions.items():
            market_value += close_prices.get(symbol, 0.0) * position.qty
        self._latest_equity = self.cash + market_value
        return self._latest_equity

    def _increase_position(self, symbol: str, qty: int, price: float) -> None:
        position = self.positions.get(symbol, Position(symbol=symbol))
        new_qty = position.qty + qty
        position.avg_price = ((position.qty * position.avg_price) + (qty * price)) / new_qty
        position.qty = new_qty
        self.positions[symbol] = position

    def _decrease_position(self, symbol: str, qty: int) -> None:
        position = self.positions.get(symbol)
        if not position:
            return
        position.qty -= qty
        if position.qty <= 0:
            del self.positions[symbol]
