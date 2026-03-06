from __future__ import annotations

import os
from typing import Any

import requests


class OpenAIClient:
    """
    Minimal OpenAI Chat Completions client for JSON trading decisions.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = 'gpt-4.1-mini',
        base_url: str = 'https://api.openai.com/v1',
        timeout_seconds: int = 30,
    ):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', '')
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError('OPENAI_API_KEY is required for OpenAIClient')

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        url = f'{self.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload: dict[str, Any] = {
            'model': self.model,
            'temperature': 0,
            'response_format': {'type': 'json_object'},
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        choices = data.get('choices', [])
        if not choices:
            raise ValueError('OpenAI response missing choices')

        message = choices[0].get('message', {})
        content = message.get('content')
        if content is None:
            raise ValueError('OpenAI response missing message content')

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            # Some APIs return content blocks.
            text_parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                maybe_text = item.get('text') or item.get('content')
                if isinstance(maybe_text, str):
                    text_parts.append(maybe_text)
            merged = ''.join(text_parts).strip()
            if merged:
                return merged

        raise ValueError('Could not parse OpenAI message content as text')

