"""
AI Analyzer v2.1 — LLM Service (OpenAI-compatible for LM Studio)
"""

import json
import logging
import time
from typing import Optional

import httpx

from app.core.config import (
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    OLLAMA_TIMEOUT,
    logger,
)

logger = logging.getLogger("ai_analyzer.ollama")


class OllamaService:
    """Async client for LM Studio (OpenAI-compatible API)."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.default_model = OLLAMA_DEFAULT_MODEL
        self.timeout = OLLAMA_TIMEOUT
        self.api_key = OLLAMA_API_KEY

    def _headers(self) -> dict:
        """Build headers. Adds Authorization only if API key is set."""
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    # ── Health / Info ───────────────────────────────────────

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{self.base_url}/v1/models", headers=self._headers()
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/v1/models", headers=self._headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []

    # ── Generation (sync) — OpenAI-compatible ──────────────────

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        format: Optional[str] = None,
    ) -> dict:
        """Generate a response via OpenAI-compatible /v1/chat/completions."""
        model = model or self.default_model
        start_time = time.time()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.debug(f"Generating with model={model}, prompt_len={len(prompt)}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )

                elapsed = time.time() - start_time

                if resp.status_code != 200:
                    logger.error(f"LLM error {resp.status_code}: {resp.text[:200]}")
                    return {
                        "success": False,
                        "error": f"LLM HTTP {resp.status_code}",
                        "response": "",
                        "model": model,
                        "elapsed": elapsed,
                    }

                data = resp.json()
                raw_response = data["choices"][0]["message"]["content"].strip()

                return {
                    "success": True,
                    "response": raw_response,
                    "model": model,
                    "elapsed": elapsed,
                }

        except httpx.TimeoutException:
            elapsed = time.time() - start_time
            logger.error(f"LLM timeout after {elapsed:.1f}s")
            return {
                "success": False,
                "error": "Timeout",
                "response": "",
                "model": model,
                "elapsed": elapsed,
            }
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"LLM generation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "model": model,
                "elapsed": elapsed,
            }

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        format: Optional[str] = None,
    ):
        """Stream not supported for LM Studio yet."""
        yield ""


# Singleton instance
ollama_service = OllamaService()