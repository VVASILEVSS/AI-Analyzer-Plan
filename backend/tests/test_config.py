"""Tests for config module."""
import os
import pytest
from unittest.mock import patch

from app.core.config import (
    get_max_concurrent_models,
    get_vram_tier,
    VALID_SIGNALS,
    VALID_TIMEFRAMES,
    VALID_REGIMES,
)


class TestVRAMDetection:
    def test_manual_vram_low(self):
        with patch.dict(os.environ, {"GPU_DETECTION": "manual", "MANUAL_VRAM_GB": "8"}):
            tier = get_vram_tier()
            assert tier == "low"

    def test_manual_vram_mid(self):
        with patch.dict(os.environ, {"GPU_DETECTION": "manual", "MANUAL_VRAM_GB": "12"}):
            tier = get_vram_tier()
            assert tier == "mid"

    def test_manual_vram_high(self):
        with patch.dict(os.environ, {"GPU_DETECTION": "manual", "MANUAL_VRAM_GB": "24"}):
            tier = get_vram_tier()
            assert tier == "high"

    def test_max_concurrent_models(self):
        with patch.dict(os.environ, {"GPU_DETECTION": "manual", "MANUAL_VRAM_GB": "8"}):
            assert get_max_concurrent_models() == 1

    def test_max_concurrent_high(self):
        with patch.dict(os.environ, {"GPU_DETECTION": "manual", "MANUAL_VRAM_GB": "24"}):
            assert get_max_concurrent_models() == 3


class TestConstants:
    def test_valid_signals(self):
        assert "BUY" in VALID_SIGNALS
        assert "SELL" in VALID_SIGNALS
        assert "HOLD" in VALID_SIGNALS

    def test_valid_timeframes(self):
        assert "1h" in VALID_TIMEFRAMES
        assert "4h" in VALID_TIMEFRAMES

    def test_valid_regimes(self):
        assert "TREND" in VALID_REGIMES
        assert "RANGE" in VALID_REGIMES
        assert "PANIC" in VALID_REGIMES
