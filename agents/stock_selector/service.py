from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agents.data_agent import DataAgent, build_default_data_agent
from config.settings import Settings, get_settings
from core.contracts.market_snapshot import LLMMarketSnapshot

from .signals import DEFAULT_SIGNAL_WEIGHTS, compute_ranking_signals, weighted_rank_score
from .universe import TradingUniverseBuilder


@dataclass
class RankedSymbol:
    symbol: str
    score: float
    signals: dict[str, float]
    as_of: datetime


class StockSelector:
    """
    Selects candidate symbols before running the trading cycle:
    1) build trading universe
    2) compute ranking signals
    3) select top N
    """

    def __init__(
        self,
        data_agent: DataAgent,
        universe_builder: TradingUniverseBuilder,
        top_n: int = 5,
        min_bars: int = 25,
        signal_weights: dict[str, float] | None = None,
    ):
        self.data_agent = data_agent
        self.universe_builder = universe_builder
        self.top_n = top_n
        self.min_bars = min_bars
        self.signal_weights = signal_weights or dict(DEFAULT_SIGNAL_WEIGHTS)

    def build_trading_universe(self) -> list[str]:
        return self.universe_builder.build_trading_universe()

    def rank_symbols(self, universe: list[str] | None = None) -> list[RankedSymbol]:
        symbols = universe or self.build_trading_universe()
        ranked: list[RankedSymbol] = []

        for symbol in symbols:
            snapshot = self.data_agent.build_snapshot(symbol=symbol)
            if len(snapshot.bars) < self.min_bars:
                continue

            signals = compute_ranking_signals(snapshot)
            score = weighted_rank_score(signals, weights=self.signal_weights)
            ranked.append(
                RankedSymbol(
                    symbol=symbol,
                    score=score,
                    signals=signals,
                    as_of=snapshot.as_of,
                )
            )

        ranked.sort(key=lambda x: x.score, reverse=True)
        return ranked

    def select_symbols(self, top_n: int | None = None, universe: list[str] | None = None) -> list[str]:
        limit = top_n if top_n is not None else self.top_n
        limit = max(0, int(limit))
        if limit == 0:
            return []

        ranked = self.rank_symbols(universe=universe)
        return [item.symbol for item in ranked[:limit]]


def build_default_stock_selector(
    settings: Settings | None = None,
    top_n: int = 5,
    min_bars: int = 25,
) -> StockSelector:
    settings = settings or get_settings()
    data_agent = build_default_data_agent(settings=settings)
    universe_builder = TradingUniverseBuilder(settings=settings)
    return StockSelector(
        data_agent=data_agent,
        universe_builder=universe_builder,
        top_n=top_n,
        min_bars=min_bars,
    )

