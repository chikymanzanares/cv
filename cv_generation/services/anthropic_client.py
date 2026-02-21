from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class AnthropicClient:
    api_key: str
    timeout_s: float = 60.0

    def generate_text(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float = 0.6,
        max_tokens: int = 2000,
    ) -> str:
        url = "https://api.anthropic.com/v1/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        content = data.get("content", [])
        if not content:
            raise RuntimeError(f"Anthropic returned no content: {data}")

        text = "".join(
            block.get("text", "")
            for block in content
            if block.get("type") == "text"
        )

        if not text.strip():
            raise RuntimeError(f"Anthropic returned empty text: {data}")

        return text