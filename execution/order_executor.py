from __future__ import annotations

from datetime import datetime

from broker.alpaca_broker import AlpacaBroker
from data.storage import OrderLog, TradeLog, get_session
from risk.risk_manager import RiskManager


class OrderExecutor:
    def __init__(self, broker: AlpacaBroker, risk_manager: RiskManager):
        self.broker = broker
        self.risk_manager = risk_manager

    def execute_signal(self, symbol: str, signal: str, latest_price: float) -> str:
        if signal == 'HOLD':
            return 'SKIPPED_HOLD'

        account = self.broker.get_account()
        cash = float(account.cash)
        equity = float(account.equity)
        start_equity = float(account.last_equity)
        open_orders = self.broker.list_open_orders()

        if not self.risk_manager.check_drawdown(starting_equity=start_equity, current_equity=equity):
            return 'SKIPPED_DRAWDOWN_LIMIT'

        if self.risk_manager.has_duplicate_open_order(symbol, signal, open_orders):
            return 'SKIPPED_DUPLICATE_ORDER'

        qty = self.risk_manager.calculate_order_qty(cash=cash, price=latest_price)
        if qty <= 0:
            return 'SKIPPED_INVALID_QTY'

        response = self.broker.place_market_order(symbol=symbol, qty=qty, side=signal)

        with get_session() as session:
            timestamp = datetime.utcnow()
            session.add(
                OrderLog(
                    symbol=symbol,
                    timestamp=timestamp,
                    side=signal,
                    qty=qty,
                    status=str(response.status),
                )
            )
            session.add(
                TradeLog(
                    symbol=symbol,
                    timestamp=timestamp,
                    side=signal,
                    qty=qty,
                    fill_price=latest_price,
                    status=str(response.status),
                )
            )
        return str(response.status)
