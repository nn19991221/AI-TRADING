from __future__ import annotations

from collections import defaultdict

from backtest.models import Bar
from data.storage import MarketBar, get_session


class HistoricalBarRepository:
    """Loads historical bars from the existing market_bars table."""

    def load(self, symbols: list[str], limit: int = 500) -> dict[str, list[Bar]]:
        bars_by_symbol: dict[str, list[Bar]] = defaultdict(list)

        with get_session() as session:
            for symbol in symbols:
                rows = (
                    session.query(MarketBar)
                    .filter(MarketBar.symbol == symbol)
                    .order_by(MarketBar.timestamp.asc())
                    .limit(limit)
                    .all()
                )
                bars_by_symbol[symbol] = [
                    Bar(
                        symbol=row.symbol,
                        timestamp=row.timestamp,
                        open=float(row.open),
                        high=float(row.high),
                        low=float(row.low),
                        close=float(row.close),
                        volume=row.volume,
                    )
                    for row in rows
                ]

        return dict(bars_by_symbol)
