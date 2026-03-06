from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


DEFAULT_TRADE_LOG_PATH = Path('logs/trades.jsonl')


def log_trade(trade_event: dict[str, Any], file_path: str | Path = DEFAULT_TRADE_LOG_PATH) -> None:
    payload = {
        'timestamp': _iso_now(trade_event.get('timestamp')),
        'symbol': str(trade_event.get('symbol', '')),
        'side': str(trade_event.get('side', 'HOLD')),
        'quantity': _to_float(trade_event.get('quantity', 0.0)),
        'price': _to_float(trade_event.get('price', 0.0)),
        'portfolio_cash': _to_float(trade_event.get('portfolio_cash', 0.0)),
        'positions': trade_event.get('positions', {}) if isinstance(trade_event.get('positions', {}), dict) else {},
    }
    _append_jsonl(file_path, payload)


def _append_jsonl(file_path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, default=str) + '\n')


def _iso_now(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

