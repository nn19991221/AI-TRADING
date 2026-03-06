from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agents.llm_agent.parser import _extract_json_object


class StrategyItemPayload(BaseModel):
    symbol: str
    market_state: str = Field(min_length=1)
    action: Literal['BUY', 'SELL', 'HOLD']
    confidence: float = Field(ge=0.0, le=1.0)
    position_size: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class StrategyBatchPayload(BaseModel):
    decisions: list[StrategyItemPayload]


def parse_strategy_batch(raw: str) -> StrategyBatchPayload:
    payload = _extract_json_object(raw)
    return StrategyBatchPayload.model_validate(payload)

