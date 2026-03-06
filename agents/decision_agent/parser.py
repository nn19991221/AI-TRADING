from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agents.llm_agent.parser import _extract_json_object


class DecisionPayload(BaseModel):
    action: Literal['BUY', 'SELL', 'HOLD']
    confidence: float = Field(ge=0.0, le=1.0)
    position_size: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)


def parse_decision(raw: str) -> DecisionPayload:
    payload = _extract_json_object(raw)
    return DecisionPayload.model_validate(payload)

