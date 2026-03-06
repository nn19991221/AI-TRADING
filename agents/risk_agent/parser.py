from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agents.llm_agent.parser import _extract_json_object


class RiskPayload(BaseModel):
    approved: bool
    reason: str = Field(min_length=1)
    adjusted_action: Literal['BUY', 'SELL', 'HOLD']
    max_position_size: float = Field(ge=0.0, le=1.0)


def parse_risk_response(raw: str) -> RiskPayload:
    payload = _extract_json_object(raw)
    return RiskPayload.model_validate(payload)

