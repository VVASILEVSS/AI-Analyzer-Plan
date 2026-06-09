"""Tests for security module."""
import pytest
from app.core.security import (
    sha256_hash,
    sha256_sign,
    sha256_verify,
    encrypt_data,
    decrypt_data,
    validate_json_schema,
    SIGNAL_ENVELOPE_SCHEMA,
)


class TestSHA256:
    def test_hash_consistency(self):
        h1 = sha256_hash("test")
        h2 = sha256_hash("test")
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_different_inputs(self):
        h1 = sha256_hash("test1")
        h2 = sha256_hash("test2")
        assert h1 != h2

    def test_sign_deterministic(self):
        obj = {"signal": "BUY", "confidence": 0.8, "pair": "BTC/USDT"}
        s1 = sha256_sign(obj)
        s2 = sha256_sign(obj)
        assert s1 == s2

    def test_verify_correct(self):
        obj = {"signal": "BUY", "confidence": 0.8}
        h = sha256_sign(obj)
        assert sha256_verify(obj, h) is True

    def test_verify_tampered(self):
        obj = {"signal": "BUY", "confidence": 0.8}
        h = sha256_sign(obj)
        obj["signal"] = "SELL"
        assert sha256_verify(obj, h) is False


class TestEncryption:
    def test_encrypt_decrypt(self):
        pytest.importorskip("cryptography")
        from app.core.security import init_fernet, FERNET_AVAILABLE
        if not FERNET_AVAILABLE:
            pytest.skip("cryptography not available")

        init_fernet("dGVzdC1rZXktZm9yLWFpLWFuYWx5emVyLTMyLWJ5dGVzLTEyMzQ1Njc4OTAxMjM0NTY=")
        encrypted = encrypt_data("secret message")
        assert encrypted is not None
        decrypted = decrypt_data(encrypted)
        assert decrypted == "secret message"

    def test_encrypt_no_key(self):
        result = encrypt_data("test")
        # Without key, should return None
        if result is not None:
            decrypt_data(result)  # Should not crash


class TestSchemaValidation:
    def test_valid_signal_envelope(self):
        valid = {
            "signal": "BUY",
            "confidence": 0.75,
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "reasons": ["Price above VWAP"],
            "risks": ["Near resistance"],
            "model_used": "qwen2.5-vl",
            "timestamp": "2026-06-08T12:00:00Z",
            "sha256": "a" * 64,
        }
        is_valid, errors = validate_json_schema(valid, SIGNAL_ENVELOPE_SCHEMA)
        assert is_valid, f"Errors: {errors}"

    def test_missing_required_field(self):
        invalid = {
            "signal": "BUY",
            "confidence": 0.75,
            "pair": "BTC/USDT",
            "timeframe": "1h",
            # Missing: reasons, risks, model_used, timestamp, sha256
        }
        is_valid, errors = validate_json_schema(invalid, SIGNAL_ENVELOPE_SCHEMA)
        assert not is_valid

    def test_invalid_signal_enum(self):
        invalid = {
            "signal": "LONG",  # Not in enum
            "confidence": 0.75,
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "reasons": ["test"],
            "risks": [],
            "model_used": "test",
            "timestamp": "2026-06-08T12:00:00Z",
            "sha256": "a" * 64,
        }
        is_valid, errors = validate_json_schema(invalid, SIGNAL_ENVELOPE_SCHEMA)
        assert not is_valid

    def test_confidence_out_of_range(self):
        invalid = {
            "signal": "BUY",
            "confidence": 1.5,  # > 1.0
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "reasons": ["test"],
            "risks": [],
            "model_used": "test",
            "timestamp": "2026-06-08T12:00:00Z",
            "sha256": "a" * 64,
        }
        is_valid, errors = validate_json_schema(invalid, SIGNAL_ENVELOPE_SCHEMA)
        assert not is_valid
