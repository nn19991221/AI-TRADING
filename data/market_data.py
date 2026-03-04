from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from broker.alpaca_broker import AlpacaBroker
from data.storage import MarketBar, get_session


class MarketDataService:
    """Fetches and persists market data bars for configured symbols."""

    def __init__(self, broker: AlpacaBroker):
        self.broker = broker

    def sync_symbol(self, symbol: str, lookback_bars: int = 100) -> int:
        rows = self.broker.fetch_30m_bars(symbol, lookback_bars=lookback_bars)
        inserted = 0
        with get_session() as session:
            for row in rows:
                ts = row['timestamp']
                exists = (
                    session.query(MarketBar)
                    .filter(MarketBar.symbol == symbol, MarketBar.timestamp == ts)
                    .first()
                )
                if exists:
                    continue
                bar = MarketBar(
                    symbol=symbol,
                    timestamp=ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts)),
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=int(row['volume']),
                )
                session.add(bar)
                inserted += 1
        return inserted

    def load_recent_closes(self, symbol: str, limit: int = 100) -> list[float]:
        with get_session() as session:
            bars = (
                session.query(MarketBar)
                .filter(MarketBar.symbol == symbol)
                .order_by(MarketBar.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [float(bar.close) for bar in reversed(bars)]
