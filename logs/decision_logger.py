from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


DEFAULT_DECISION_LOG_PATH = Path('logs/decisions.jsonl')


def log_decision(event: dict[str, Any], file_path: str | Path = DEFAULT_DECISION_LOG_PATH) -> None:
    payload = {
        'timestamp': _iso_now(event.get('timestamp')),
        'symbol': str(event.get('symbol', '')),
        'agent': str(event.get('agent', '')),
        'action': str(event.get('action', 'HOLD')),
        'confidence': _to_float(event.get('confidence', 0.0)),
        'reason': str(event.get('reason', '')),
        'price': _to_float(event.get('price', 0.0)),
        'volatility': _to_float(event.get('volatility', 0.0)),
        'next_check_minutes': _to_int(event.get('next_check_minutes', 0)),
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


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

