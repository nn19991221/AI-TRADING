from __future__ import annotations

import os

from agents.llm_agent.client import OpenAIClient


class MarketAgentClient(OpenAIClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = 'https://api.openai.com/v1',
        timeout_seconds: int = 30,
    ):
        super().__init__(
            api_key=api_key or os.getenv('OPENAI_API_KEY', ''),
            model=model or os.getenv('LLM_MARKET_MODEL', 'gpt-4.1-mini'),
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

