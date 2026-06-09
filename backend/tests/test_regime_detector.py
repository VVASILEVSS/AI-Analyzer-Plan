"""Tests for Regime Detector."""
import pytest
from app.services.regime_detector import RegimeDetector


@pytest.fixture
def detector():
    return RegimeDetector()


class TestRegimeDetector:
    def test_trend_detection(self, detector):
        market_data = {
            "close": 68000,
            "open": 67000,
            "high": 68500,
            "low": 66800,
            "volume": 2000,
            "volume_ma": 1500,
            "adx": 30,
            "rsi": 65,
            "macd_hist": 50,
            "bb_width": 0.04,
            "ema_9": 67800,
            "ema_21": 67200,
            "ema_50": 65000,
            "atr": 400,
            "funding_rate": 0.0001,
            "oi_change_pct": 2.0,
        }
        result = detector.detect(market_data)
        assert result["regime"] in ["TREND", "RANGE", "ACCUMULATION", "DISTRIBUTION", "PANIC"]
        assert 0 <= result["confidence"] <= 1
        assert "indicators" in result

    def test_range_detection(self, detector):
        market_data = {
            "close": 67000,
            "open": 66900,
            "high": 67100,
            "low": 66800,
            "volume": 1000,
            "volume_ma": 1000,
            "adx": 10,
            "rsi": 50,
            "macd_hist": 0,
            "bb_width": 0.005,
            "ema_9": 67000,
            "ema_21": 67000,
            "ema_50": 67000,
            "atr": 100,
        }
        result = detector.detect(market_data)
        assert result["regime"] in ["RANGE", "ACCUMULATION"]

    def test_panic_detection(self, detector):
        market_data = {
            "close": 60000,
            "open": 66000,
            "high": 66500,
            "low": 59000,
            "volume": 8000,
            "volume_ma": 1500,
            "adx": 50,
            "rsi": 15,
            "macd_hist": -200,
            "bb_width": 0.12,
            "ema_9": 65000,
            "ema_21": 66000,
            "ema_50": 67000,
            "atr": 2000,
            "funding_rate": -0.005,
            "oi_change_pct": -15,
        }
        result = detector.detect(market_data)
        assert result["regime"] == "PANIC"
        assert result["confidence"] > 0

    def test_empty_data(self, detector):
        result = detector.detect({})
        assert result["regime"] in ["TREND", "RANGE", "ACCUMULATION", "DISTRIBUTION", "PANIC"]
