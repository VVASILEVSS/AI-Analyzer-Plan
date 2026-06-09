"""
AI Analyzer v2.1 — Cache Service
SHA256-based request cache. Avoids redundant LLM calls.
Migrated from v1 — already exists in LOCAL_AI_ENGINE.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from app.core.config import CACHE_ENABLED, CACHE_SHA256, CACHE_TTL_HOURS, logger
from app.core.security import sha256_sign

logger = logging.getLogger("ai_analyzer.cache")


class CacheService:
    """File-based SHA256 cache for signal requests."""

    def __init__(self, cache_path: Optional[str] = None, ttl_hours: int = CACHE_TTL_HOURS):
        self.cache_path = Path(cache_path or CACHE_SHA256)
        self.ttl_hours = ttl_hours
        self._cache: dict = {}
        self._dirty = False
        self._load()

    def _load(self):
        """Load cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"Cache loaded: {len(self._cache)} entries")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cache = {}
        else:
            self._cache = {}

    def _save(self):
        """Save cache to disk (only if dirty)."""
        if not self._dirty:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            self._dirty = False
            logger.debug(f"Cache saved: {len(self._cache)} entries")
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")

    def _make_key(self, data: dict) -> str:
        """Generate cache key from request data."""
        # Use only fields that affect the signal output
        key_data = {
            "pair": data.get("pair", ""),
            "timeframe": data.get("timeframe", ""),
            "model": data.get("model", ""),
            "market_data_hash": sha256_sign(
                data.get("market_data", {})
            ) if data.get("market_data") else "no_data",
        }
        return sha256_sign(key_data)

    def get(self, request_data: dict) -> Optional[dict]:
        """
        Look up a cached signal. Returns None if not found or expired.
        """
        if not CACHE_ENABLED:
            return None

        key = self._make_key(request_data)
        entry = self._cache.get(key)

        if entry is None:
            logger.debug(f"Cache miss: {key[:16]}...")
            return None

        # Check TTL
        cached_time = entry.get("cached_at", 0)
        ttl_seconds = self.ttl_hours * 3600
        if time.time() - cached_time > ttl_seconds:
            logger.debug(f"Cache expired: {key[:16]}...")
            del self._cache[key]
            self._dirty = True
            self._save()
            return None

        logger.info(f"Cache hit: {key[:16]}...")
        return entry.get("signal")

    def put(self, request_data: dict, signal: dict):
        """
        Store a signal in cache.
        """
        if not CACHE_ENABLED:
            return

        key = self._make_key(request_data)
        self._cache[key] = {
            "signal": signal,
            "cached_at": time.time(),
        }
        self._dirty = True
        # Don't save immediately — will be saved on next get() miss or explicit flush
        self._save()
        logger.debug(f"Cache put: {key[:16]}...")

    def flush(self):
        """Force save cache to disk."""
        self._save()

    def clear_expired(self):
        """Remove all expired entries."""
        if not CACHE_ENABLED:
            return

        ttl_seconds = self.ttl_hours * 3600
        now = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if now - v.get("cached_at", 0) > ttl_seconds
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self._dirty = True
            self._save()
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "total_entries": len(self._cache),
            "enabled": CACHE_ENABLED,
            "ttl_hours": self.ttl_hours,
            "cache_path": str(self.cache_path),
        }


# Singleton instance
cache_service = CacheService()
