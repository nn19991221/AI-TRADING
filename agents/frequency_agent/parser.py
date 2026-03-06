from __future__ import annotations

from pydantic import BaseModel, Field

from agents.llm_agent.parser import _extract_json_object


class FrequencyPayload(BaseModel):
    next_check_minutes: int = Field(ge=1, le=15)
    reason: str = Field(min_length=1)


def parse_frequency_response(raw: str) -> FrequencyPayload:
    payload = _extract_json_object(raw)
    return FrequencyPayload.model_validate(payload)
