from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_MARKET_CACHE_PATH = Path('state/market_cache.json')


class MarketStateCache:
    """
    Reuses previous strategy output for low-volatility symbols.
    If volatility is low, cached market state can be reused for up to 2 cycles.
    """

    def __init__(self, file_path: str | Path = DEFAULT_MARKET_CACHE_PATH):
        self.file_path = Path(file_path)
        self._cache = self._load()

    def get_cached_decision(self, symbol: str, volatility: str) -> dict[str, Any] | None:
        item = self._cache.get(symbol.upper())
        if not isinstance(item, dict):
            return None

        if volatility != 'low':
            return None

        remaining = int(item.get('reuse_remaining', 0))
        if remaining <= 0:
            return None

        item['reuse_remaining'] = remaining - 1
        self._persist()
        decision = item.get('decision')
        return decision if isinstance(decision, dict) else None

    def update(self, symbol: str, volatility: str, decision_payload: dict[str, Any]) -> None:
        reuse_remaining = 2 if volatility == 'low' else 0
        self._cache[symbol.upper()] = {
            'volatility': volatility,
            'reuse_remaining': reuse_remaining,
            'decision': decision_payload,
        }
        self._persist()

    def clear(self) -> None:
        self._cache = {}
        self._persist()

    def _load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            return {}
        try:
            payload = json.loads(self.file_path.read_text(encoding='utf-8'))
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return {}

    def _persist(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(self._cache, ensure_ascii=True, indent=2, default=str),
            encoding='utf-8',
        )

