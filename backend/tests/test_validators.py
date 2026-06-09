"""Tests for validators module."""
import pytest
from app.core.validators import (
    validate_signal_envelope,
    build_signal_envelope,
    validate_llm_response,
    ValidationError,
)


class TestValidateSignalEnvelope:
    def test_valid_envelope(self):
        envelope = {
            "signal": "BUY",
            "confidence": 0.75,
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "reasons": ["Price above VWAP"],
            "risks": ["Near resistance"],
            "model_used": "qwen2.5-vl",
            "timestamp": "2026-06-08T12:00:00+00:00",
            "sha256": "a" * 64,
        }
        result = validate_signal_envelope(envelope)
        assert result["signal"] == "BUY"
        assert result["confidence"] == 0.75

    def test_missing_reasons(self):
        envelope = {
            "signal": "BUY",
            "confidence": 0.75,
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "reasons": [],  # Empty
            "risks": [],
            "model_used": "test",
            "timestamp": "2026-06-08T12:00:00+00:00",
            "sha256": "a" * 64,
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_signal_envelope(envelope)
        assert any("reason" in e.lower() for e in exc_info.value.errors)

    def test_invalid_pair(self):
        envelope = {
            "signal": "BUY",
            "confidence": 0.75,
            "pair": "BTCUSDT",  # No slash
            "timeframe": "1h",
            "reasons": ["test"],
            "risks": [],
            "model_used": "test",
            "timestamp": "2026-06-08T12:00:00+00:00",
            "sha256": "a" * 64,
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_signal_envelope(envelope)
        assert any("pair" in e.lower() for e in exc_info.value.errors)

    def test_normalization(self):
        envelope = {
            "signal": "buy",
            "confidence": 0.75123,
            "pair": "btc/usdt",
            "timeframe": "1h",
            "reasons": ["test"],
            "risks": ["risk1"],
            "model_used": "test",
            "timestamp": "2026-06-08T12:00:00+00:00",
            "sha256": "a" * 64,
        }
        result = validate_signal_envelope(envelope)
        assert result["signal"] == "BUY"
        assert result["pair"] == "BTC/USDT"
        assert result["confidence"] == 0.7512


class TestBuildSignalEnvelope:
    def test_basic_build(self):
        envelope = build_signal_envelope(
            signal="BUY",
            confidence=0.8,
            pair="BTC/USDT",
            timeframe="1h",
            reasons=["OI growing"],
            risks=["RSI overbought"],
            model_used="qwen2.5-vl",
        )
        assert envelope["signal"] == "BUY"
        assert envelope["sha256"]  # Auto-generated
        assert envelope["timestamp"]  # Auto-generated
        assert len(envelope["reasons"]) == 1

    def test_low_confidence_forces_hold(self):
        envelope = build_signal_envelope(
            signal="BUY",
            confidence=0.1,  # Below minimum
            pair="BTC/USDT",
            timeframe="1h",
            reasons=["test"],
            risks=[],
            model_used="test",
        )
        assert envelope["signal"] == "HOLD"
        assert any("threshold" in r.lower() for r in envelope["reasons"])

    def test_with_optional_fields(self):
        envelope = build_signal_envelope(
            signal="SELL",
            confidence=0.7,
            pair="ETH/USDT",
            timeframe="4h",
            reasons=["test"],
            risks=[],
            model_used="test",
            regime="TREND",
            ml_verdict="PASS",
            ml_probability=0.85,
        )
        assert envelope["regime"] == "TREND"
        assert envelope["ml_verdict"] == "PASS"
        assert envelope["ml_probability"] == 0.85


class TestValidateLLMResponse:
    def test_valid_json_response(self):
        raw = '{"signal": "BUY", "confidence": 0.75, "reasons": ["test"], "risks": []}'
        result = validate_llm_response(raw)
        assert result["signal"] == "BUY"
        assert result["confidence"] == 0.75

    def test_json_in_code_block(self):
        raw = '```json\n{"signal": "SELL", "confidence": 0.6, "reasons": ["test"], "risks": []}\n```'
        result = validate_llm_response(raw)
        assert result["signal"] == "SELL"

    def test_json_with_surrounding_text(self):
        raw = 'Here is the analysis:\n{"signal": "HOLD", "confidence": 0.4, "reasons": ["indecisive"], "risks": ["volatile"]}\nEnd of analysis.'
        result = validate_llm_response(raw)
        assert result["signal"] == "HOLD"

    def test_invalid_json(self):
        raw = 'This is not JSON at all'
        with pytest.raises(ValidationError):
            validate_llm_response(raw)

    def test_missing_signal_field(self):
        raw = '{"confidence": 0.5, "reasons": []}'
        with pytest.raises(ValidationError):
            validate_llm_response(raw)

    def test_invalid_signal_value(self):
        raw = '{"signal": "LONG", "confidence": 0.5, "reasons": ["test"], "risks": []}'
        with pytest.raises(ValidationError):
            validate_llm_response(raw)
