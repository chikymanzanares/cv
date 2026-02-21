from __future__ import annotations

import base64
import random
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx


class GeminiRateLimitError(RuntimeError):
    """Raised when Gemini is rate-limited or quota-limited (HTTP 429 / 403 quota)."""


@dataclass(frozen=True)
class GeminiClient:
    api_key: str
    timeout_s: float = 60.0

    def _url(self, model: str) -> str:
        model_id = model.replace("models/", "")
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"

    def _post_with_retry(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        IMPORTANT FOR FREE TIER:
        - If Gemini returns 429 → DO NOT retry → fallback immediately upstream
        - Retry ONLY on true transient errors (503/504)
        """
        max_attempts = 3
        base_sleep = 1.0
        last_resp: httpx.Response | None = None

        with httpx.Client(timeout=self.timeout_s) as client:
            for attempt in range(1, max_attempts + 1):
                r = client.post(url, headers=headers, json=payload)
                last_resp = r

                # 🔴 FREE-TIER QUOTA → DO NOT RETRY
                if r.status_code == 429:
                    raise GeminiRateLimitError("Gemini 429 (likely free-tier quota exhausted).")

                # 🟡 Retry ONLY transient infra issues
                if r.status_code in (503, 504):
                    sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    print(f"[Gemini] transient {r.status_code}, retry in {sleep_s:.1f}s...")
                    time.sleep(min(sleep_s, 10))
                    continue

                # Sometimes quota shows up as 403
                if r.status_code == 403:
                    try:
                        body = r.json()
                    except Exception:
                        body = {"raw": r.text[:500]}
                    msg = str(body).lower()
                    if "quota" in msg or "rate" in msg or "exceeded" in msg:
                        raise GeminiRateLimitError(f"Gemini quota/rate limit: {msg}")
                    r.raise_for_status()

                r.raise_for_status()
                return r.json()

        raise GeminiRateLimitError("Gemini request failed after retries.")

    def generate_text(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float = 0.6,
    ) -> str:
        url = self._url(model)

        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        data = self._post_with_retry(url=url, headers=headers, payload=payload)

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))

        if not text.strip():
            raise RuntimeError(f"Gemini returned empty text: {data}")

        return text

    def generate_image_png_bytes(
        self,
        *,
        model: str,
        prompt: str,
        aspect_ratio: str = "1:1",
        fallback_loader: Callable[[], bytes] | None = None,
    ) -> bytes:
        url = self._url(model)

        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["Image"],
                "imageConfig": {"aspectRatio": aspect_ratio},
            },
        }

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            data = self._post_with_retry(url=url, headers=headers, payload=payload)
        except GeminiRateLimitError:
            if fallback_loader is not None:
                print("[Gemini] Image quota hit → using local fallback")
                return fallback_loader()
            raise

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        for p in parts:
            if not isinstance(p, dict):
                continue
            inline = p.get("inlineData") or p.get("inline_data")
            if inline and isinstance(inline, dict):
                b64 = inline.get("data")
                if b64:
                    return base64.b64decode(b64)

        raise RuntimeError(f"No inline image data found in response: {data}")