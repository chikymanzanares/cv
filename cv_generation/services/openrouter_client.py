from __future__ import annotations

import time
import random
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class OpenRouterClient:
    api_key: str
    timeout_s: float = 60.0
    min_interval_s: float = 12.0

    _last_request_ts: float = 0.0

    def _throttle(self) -> None:
        now = time.time()
        elapsed = now - self._last_request_ts
        if elapsed < self.min_interval_s:
            sleep_s = self.min_interval_s - elapsed
            print(f"[OpenRouter] Throttling: sleeping {sleep_s:.1f}s to respect free-tier limits...")
            time.sleep(sleep_s)
        self._last_request_ts = time.time()

    def _post_with_retry(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        max_attempts = 6
        base_sleep = 2.0
        last_resp = None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout_s) as client:
            for attempt in range(1, max_attempts + 1):
                self._throttle()

                r = client.post(url, headers=headers, json=payload)
                last_resp = r

                if r.status_code in (429, 503, 504):
                    sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    print(f"[OpenRouter] 429 retrying in {sleep_s:.1f}s...")
                    time.sleep(min(sleep_s, 30))
                    continue

                r.raise_for_status()
                return r.json()

        raise RuntimeError(f"OpenRouter failed after retries: {last_resp.text[:500]}")

    def chat_completion_text(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        data = self._post_with_retry(url, payload)

        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            raise RuntimeError(f"Unexpected OpenRouter response: {data}")