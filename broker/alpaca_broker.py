from __future__ import annotations

from datetime import datetime, timedelta

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from config.settings import Settings


class AlpacaBroker:
    """Abstraction over Alpaca trading and market data clients."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.trading = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=True,
        )
        self.data = StockHistoricalDataClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
        )

    def fetch_30m_bars(self, symbol: str, lookback_bars: int = 100):
        end = datetime.utcnow()
        start = end - timedelta(minutes=30 * lookback_bars)
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame(30, TimeFrameUnit.Minute),
            start=start,
            end=end,
            feed=self.settings.data_feed,
        )
        bars = self.data.get_stock_bars(request)
        return bars.df.reset_index().to_dict(orient='records')

    def place_market_order(self, symbol: str, qty: int, side: str):
        order = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side.upper() == 'BUY' else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        return self.trading.submit_order(order_data=order)

    def get_account(self):
        return self.trading.get_account()

    def get_positions(self):
        return self.trading.get_all_positions()

    def list_open_orders(self):
        return self.trading.get_orders()
