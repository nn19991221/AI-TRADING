from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PORTFOLIO_PATH = Path('state/portfolio.json')


def save_portfolio_state(state: dict[str, Any], file_path: str | Path = DEFAULT_PORTFOLIO_PATH) -> None:
    payload = {
        'cash': _to_float(state.get('cash', 0.0)),
        'positions': state.get('positions', {}) if isinstance(state.get('positions', {}), dict) else {},
        'realized_pnl': _to_float(state.get('realized_pnl', 0.0)),
        'unrealized_pnl': _to_float(state.get('unrealized_pnl', 0.0)),
    }
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding='utf-8')


def load_portfolio_state(file_path: str | Path = DEFAULT_PORTFOLIO_PATH) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return _default_state()
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return _default_state()

    if not isinstance(payload, dict):
        return _default_state()

    return {
        'cash': _to_float(payload.get('cash', 0.0)),
        'positions': payload.get('positions', {}) if isinstance(payload.get('positions', {}), dict) else {},
        'realized_pnl': _to_float(payload.get('realized_pnl', 0.0)),
        'unrealized_pnl': _to_float(payload.get('unrealized_pnl', 0.0)),
    }


def _default_state() -> dict[str, Any]:
    return {
        'cash': 0.0,
        'positions': {},
        'realized_pnl': 0.0,
        'unrealized_pnl': 0.0,
    }


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

