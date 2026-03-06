from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field


class DecisionPayload(BaseModel):
    action: Literal['BUY', 'SELL', 'HOLD']
    confidence: float = Field(ge=0.0, le=1.0)
    position_size: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)


def parse_decision_json(raw: str) -> DecisionPayload:
    payload_dict = _extract_json_object(raw)
    return DecisionPayload.model_validate(payload_dict)


def to_trading_decision(symbol: str, payload: DecisionPayload):
    from orchestrator.trading_cycle import TradingDecision

    return TradingDecision(
        symbol=symbol,
        action=payload.action,
        confidence=payload.confidence,
        rationale=payload.reasoning,
        meta={'position_size': payload.position_size},
    )


def _extract_json_object(raw: str) -> dict:
    text = raw.strip()
    if not text:
        raise ValueError('LLM response was empty')

    try:
        decoded = json.loads(text)
        if isinstance(decoded, dict):
            return decoded
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ValueError('LLM response does not contain a JSON object')

    candidate = text[start : end + 1]
    decoded = json.loads(candidate)
    if not isinstance(decoded, dict):
        raise ValueError('LLM JSON payload must be an object')
    return decoded
