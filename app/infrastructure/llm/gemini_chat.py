from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import httpx

from app.domain.chat.services.llm_chat_service import LLMChatService

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

logger = logging.getLogger(__name__)


class GeminiChatService(LLMChatService):
    """
    Streams chat completions from the Google Gemini API using Server-Sent Events.

    Uses the streamGenerateContent endpoint with alt=sse.
    The system parameter maps to Gemini's systemInstruction field.
    Message roles are translated: "assistant" → "model" (Gemini convention).
    """

    def __init__(self, *, api_key: str, model: str = "models/gemini-2.0-flash"):
        self._api_key = api_key
        self._model = model.removeprefix("models/")

    def stream(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        url = f"{_BASE_URL}/{self._model}:streamGenerateContent?alt=sse&key={self._api_key}"

        contents = [
            {
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}],
            }
            for msg in messages
        ]

        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }

        logger.info("Gemini stream | model=%s | messages=%d", self._model, len(messages))
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", url, headers={"Content-Type": "application/json"}, json=payload) as response:
                response.raise_for_status()
                logger.debug("Gemini HTTP %s", response.status_code)
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    candidates = chunk.get("candidates", [])
                    if not candidates:
                        continue
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if isinstance(part, dict):
                            text = part.get("text", "")
                            if text:
                                yield text
