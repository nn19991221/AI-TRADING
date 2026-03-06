from __future__ import annotations

from config.settings import Settings, get_settings


class TradingUniverseBuilder:
    """
    Builds the candidate trading universe.
    Default behavior uses configured symbols from Settings.
    """

    def __init__(self, settings: Settings | None = None, static_symbols: list[str] | None = None):
        self.settings = settings or get_settings()
        self.static_symbols = static_symbols or []

    def build_trading_universe(self) -> list[str]:
        raw = self.static_symbols or self.settings.symbol_list

        deduped: list[str] = []
        seen: set[str] = set()
        for symbol in raw:
            normalized = symbol.strip().upper()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

