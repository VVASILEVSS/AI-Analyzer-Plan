"""
AI Analyzer v2.1 — Watchdog
Process monitoring for LM Studio / Ollama.
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.core.config import OLLAMA_BASE_URL, logger

WATCHDOG_CHECK_INTERVAL_S: int = 30
WATCHDOG_MAX_RETRIES: int = 3
WATCHDOG_COOLDOWN_S: int = 60
WATCHDOG_TIMEOUT_S: int = 10


class OllamaWatchdog:
    """Monitors LLM server (LM Studio / Ollama) and reports status."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        check_interval: int = WATCHDOG_CHECK_INTERVAL_S,
        max_retries: int = WATCHDOG_MAX_RETRIES,
        cooldown: int = WATCHDOG_COOLDOWN_S,
    ):
        self.base_url = base_url.rstrip("/")
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.cooldown = cooldown
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._fail_count = 0
        self._last_restart: float = 0
        self._status = "initialized"

    async def health_check(self) -> bool:
        """Check if LLM server is responding."""
        try:
            async with httpx.AsyncClient(timeout=WATCHDOG_TIMEOUT_S) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
            return False
        except Exception as e:
            logger.error(f"Watchdog health check error: {e}")
            return False

    async def get_loaded_models(self) -> list[str]:
        """Get list of available models from LLM server."""
        try:
            async with httpx.AsyncClient(timeout=WATCHDOG_TIMEOUT_S) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            pass
        return []

    async def _watch_loop(self):
        """Main watchdog loop."""
        logger.info("Watchdog started — monitoring LLM server")
        while self._running:
            try:
                healthy = await self.health_check()

                if healthy:
                    self._status = "healthy"
                    self._fail_count = 0
                    logger.debug("LLM health check: OK")
                else:
                    self._status = "unhealthy"
                    self._fail_count += 1
                    logger.warning("LLM health check: FAILED")
                    if self._fail_count >= self.max_retries:
                        logger.error(
                            f"Watchdog: LLM server not responding after {self.max_retries} checks. "
                            "Check that LM Studio server is running."
                        )
                        self._status = "down"

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog loop error: {e}")

            await asyncio.sleep(self.check_interval)

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("Watchdog started")

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Watchdog stopped")

    def get_status(self) -> dict:
        return {
            "status": self._status,
            "running": self._running,
            "fail_count": self._fail_count,
            "max_retries": self.max_retries,
        }


# Singleton instance
watchdog = OllamaWatchdog()