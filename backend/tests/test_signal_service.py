"""Tests for Signal Service."""
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services.signal_service import SignalService


@pytest.fixture
def signal_svc(tmp_path):
    service = SignalService()
    # Override signals path for testing
    from app.core import config
    original_path = config.SIGNALS_JSONL
    config.SIGNALS_JSONL = tmp_path / "test_signals.jsonl"
    yield service
    config.SIGNALS_JSONL = original_path


class TestSignalService:
    @pytest.mark.asyncio
    async def test_generate_signal_with_cache(self, signal_svc):
        # Mock cache hit
        with patch("app.services.signal_service.cache_service") as mock_cache:
            mock_cache.get.return_value = {
                "signal": "BUY",
                "confidence": 0.8,
                "pair": "BTC/USDT",
                "from_cache": False,
            }
            result = await signal_svc.generate_signal(
                pair="BTC/USDT",
                timeframe="1h",
            )
            assert result.get("from_cache") is True
            assert result["signal"] == "BUY"

    @pytest.mark.asyncio
    async def test_generate_signal_llm_error(self, signal_svc):
        with patch("app.services.signal_service.cache_service") as mock_cache:
            mock_cache.get.return_value = None  # Cache miss

        with patch("app.services.signal_service.ml_filter_service") as mock_ml:
            mock_ml.predict.return_value = {"verdict": "PASS", "probability": 0.8, "blocked": False, "phase": "log_only"}

        with patch("app.services.signal_service.ollama_service") as mock_ollama:
            mock_ollama.generate.return_value = {
                "success": False,
                "error": "Connection refused",
                "response": "",
                "model": "test",
                "elapsed": 0.1,
            }

            result = await signal_svc.generate_signal(
                pair="BTC/USDT",
                timeframe="1h",
            )
            assert result["success"] is False
            assert "error" in result

    def test_get_signals_empty(self, signal_svc):
        result = signal_svc.get_signals()
        assert result["signals"] == []
        assert result["total"] == 0

    def test_save_and_get_signals(self, signal_svc, tmp_path):
        signal = {
            "signal": "BUY",
            "confidence": 0.8,
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "reasons": ["test"],
            "risks": [],
            "model_used": "test",
            "timestamp": "2026-06-08T12:00:00Z",
            "sha256": "a" * 64,
        }
        signal_svc._save_signal(signal)
        signal_svc._save_signal({**signal, "pair": "ETH/USDT"})

        result = signal_svc.get_signals()
        assert result["total"] == 2

        # Filter by pair
        btc = signal_svc.get_signals(pair="BTC/USDT")
        assert btc["total"] == 1

    def test_stats(self, signal_svc, tmp_path):
        signal = {
            "signal": "BUY",
            "confidence": 0.8,
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "reasons": ["test"],
            "risks": [],
            "model_used": "test",
            "timestamp": "2026-06-08T12:00:00Z",
            "sha256": "a" * 64,
        }
        signal_svc._save_signal(signal)
        stats = signal_svc.get_stats()
        assert stats["total_stored"] == 1
        assert stats["by_signal"]["BUY"] == 1
