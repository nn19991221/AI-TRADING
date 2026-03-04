from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from broker.alpaca_broker import AlpacaBroker
from data.storage import PortfolioSnapshot, get_session


class PortfolioManager:
    def __init__(self, broker: AlpacaBroker):
        self.broker = broker

    def snapshot(self) -> dict:
        account = self.broker.get_account()
        positions = self.broker.get_positions()

        cash = Decimal(str(account.cash))
        equity = Decimal(str(account.equity))
        last_equity = Decimal(str(account.last_equity))
        daily_pnl = equity - last_equity

        with get_session() as session:
            session.add(
                PortfolioSnapshot(
                    timestamp=datetime.utcnow(),
                    cash=cash,
                    equity=equity,
                    daily_pnl=daily_pnl,
                )
            )

        return {
            'cash': float(cash),
            'equity': float(equity),
            'daily_pnl': float(daily_pnl),
            'positions': [
                {
                    'symbol': p.symbol,
                    'qty': p.qty,
                    'market_value': p.market_value,
                    'unrealized_pl': p.unrealized_pl,
                }
                for p in positions
            ],
        }
