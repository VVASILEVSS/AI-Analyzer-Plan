"""Tests for Cache Service."""
import json
import time
import pytest
from pathlib import Path
from app.services.cache_service import CacheService


@pytest.fixture
def cache(tmp_path):
    cache_path = tmp_path / "test_cache.json"
    service = CacheService(str(cache_path), ttl_hours=1)
    return service


class TestCacheService:
    def test_put_and_get(self, cache):
        request = {"pair": "BTC/USDT", "timeframe": "1h", "model": "test"}
        signal = {"signal": "BUY", "confidence": 0.8}
        cache.put(request, signal)
        result = cache.get(request)
        assert result is not None
        assert result["signal"] == "BUY"

    def test_cache_miss(self, cache):
        request = {"pair": "ETH/USDT", "timeframe": "1h"}
        result = cache.get(request)
        assert result is None

    def test_different_requests_different_keys(self, cache):
        req1 = {"pair": "BTC/USDT", "timeframe": "1h", "model": "test"}
        req2 = {"pair": "ETH/USDT", "timeframe": "1h", "model": "test"}
        cache.put(req1, {"signal": "BUY"})
        cache.put(req2, {"signal": "SELL"})
        assert cache.get(req1)["signal"] == "BUY"
        assert cache.get(req2)["signal"] == "SELL"

    def test_ttl_expiration(self, cache):
        cache.ttl_hours = 0  # Immediate expiration
        request = {"pair": "BTC/USDT", "timeframe": "1h", "model": "test"}
        cache.put(request, {"signal": "BUY"})
        time.sleep(0.1)
        result = cache.get(request)
        assert result is None

    def test_persistence(self, cache):
        request = {"pair": "BTC/USDT", "timeframe": "1h", "model": "test"}
        cache.put(request, {"signal": "HOLD"})

        # Create new cache instance from same file
        cache2 = CacheService(str(cache.cache_path), ttl_hours=1)
        result = cache2.get(request)
        assert result is not None
        assert result["signal"] == "HOLD"

    def test_stats(self, cache):
        stats = cache.stats()
        assert "total_entries" in stats
        assert "ttl_hours" in stats

    def test_clear_expired(self, cache):
        request = {"pair": "BTC/USDT", "timeframe": "1h", "model": "test"}
        cache.ttl_hours = 0
        cache.put(request, {"signal": "BUY"})
        cache.clear_expired()
        stats = cache.stats()
        assert stats["total_entries"] == 0
