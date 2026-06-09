"""Tests for ML Filter service."""
import numpy as np
import pytest
from app.services.ml_filter_service import MLFilterService


@pytest.fixture
def ml_service():
    service = MLFilterService()
    service._enabled = True
    return service


class TestMLFilterService:
    def test_predict_disabled(self):
        service = MLFilterService()
        service._enabled = False
        result = service.predict({})
        assert result["verdict"] == "PASS"
        assert result["phase"] == "disabled"

    def test_predict_no_model(self):
        service = MLFilterService()
        service._enabled = True
        # Model file doesn't exist
        result = service.predict({})
        assert result["verdict"] == "PASS"
        assert result["phase"] == "unloaded"

    def test_feature_extraction(self):
        service = MLFilterService()
        market_data = {
            "close": 67000,
            "open": 66500,
            "high": 67500,
            "low": 66000,
            "volume": 1500,
            "price_change_pct": 0.75,
            "volume_change_pct": 1.2,
            "volatility": 0.023,
            "rsi": 65,
            "macd": 120,
            "macd_signal": 80,
            "macd_hist": 40,
            "bb_upper": 69000,
            "bb_middle": 67000,
            "bb_lower": 65000,
            "bb_width": 0.03,
            "ema_9": 67200,
            "ema_21": 66800,
            "ema_50": 65000,
            "atr": 500,
            "adx": 28,
            "obv": 50000,
            "vwap": 66800,
            "oi": 18000000,
            "oi_change_pct": 2.5,
            "cvd": 500,
            "funding_rate": 0.0001,
            "long_short_ratio": 1.2,
            "volume_ma": 1200,
            "momentum": 0.5,
        }
        features = service.extract_features(market_data)
        assert features is not None
        assert len(features) == 50
        assert all(isinstance(f, (int, float, np.floating)) for f in features)

    def test_feature_extraction_empty(self):
        service = MLFilterService()
        features = service.extract_features({})
        assert features is not None
        assert len(features) == 50

    def test_phase_switching(self):
        service = MLFilterService()
        assert service._phase == "log_only"
        service.set_phase("active")
        assert service._phase == "active"
        with pytest.raises(ValueError):
            service.set_phase("invalid")

    def test_stats(self):
        service = MLFilterService()
        service._enabled = True
        assert not service.is_active  # No model loaded
