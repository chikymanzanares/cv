from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import httpx

from app.domain.chat.services.llm_chat_service import LLMChatService

_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"

logger = logging.getLogger(__name__)


class AnthropicChatService(LLMChatService):
    """
    Streams chat completions from the Anthropic Messages API using Server-Sent Events.

    The system parameter is passed as Anthropic's top-level system field (not as a message),
    which is the idiomatic way to provide context/persona without consuming conversation turns.
    """

    def __init__(self, *, api_key: str, model: str = "claude-3-haiku-20240307"):
        self._api_key = api_key
        self._model = model

    def stream(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
            "stream": True,
        }

        logger.info("Anthropic stream | model=%s | messages=%d", self._model, len(messages))
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", _API_URL, headers=headers, json=payload) as response:
                response.raise_for_status()
                logger.debug("Anthropic HTTP %s", response.status_code)
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield text
