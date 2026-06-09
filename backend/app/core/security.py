"""
AI Analyzer v2.1 — Security Module
Fernet encryption/decryption, SHA256 signing/verification, JSON Schema validation.
Migrated from v1 security.py — no functional changes.
"""

import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger("ai_analyzer.security")

# ── Fernet Encryption ───────────────────────────────────────

try:
    from cryptography.fernet import Fernet, InvalidToken

    _fernet_key = None
    _fernet = None

    def init_fernet(key: Optional[str] = None):
        """Initialize Fernet with key from config or environment."""
        global _fernet_key, _fernet
        from app.core.config import FERNET_KEY
        k = key or FERNET_KEY
        if k:
            _fernet_key = k.encode() if isinstance(k, str) else k
            _fernet = Fernet(_fernet_key)
            logger.info("Fernet encryption initialized")
        else:
            logger.warning("No FERNET_KEY provided — encryption disabled")

    def encrypt_data(data: str) -> Optional[str]:
        """Encrypt string data with Fernet. Returns None if not initialized."""
        if _fernet is None:
            init_fernet()
        if _fernet is None:
            logger.warning("Encryption requested but Fernet not initialized")
            return None
        try:
            return _fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None

    def decrypt_data(encrypted: str) -> Optional[str]:
        """Decrypt Fernet-encrypted string. Returns None on failure."""
        if _fernet is None:
            init_fernet()
        if _fernet is None:
            return None
        try:
            return _fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            logger.error("Decryption failed: invalid token")
            return None
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

    FERNET_AVAILABLE = True

except ImportError:
    FERNET_AVAILABLE = False

    def encrypt_data(data: str) -> Optional[str]:
        logger.warning("cryptography not installed — encryption unavailable")
        return None

    def decrypt_data(encrypted: str) -> Optional[str]:
        return None

    def init_fernet(key: Optional[str] = None):
        logger.warning("cryptography not installed — Fernet disabled")


# ── SHA256 ──────────────────────────────────────────────────

def sha256_hash(data: str) -> str:
    """Compute SHA256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sha256_sign(obj: dict) -> str:
    """Create deterministic SHA256 from JSON-serialized dict (sorted keys)."""
    serialized = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return sha256_hash(serialized)


def sha256_verify(obj: dict, expected_hash: str) -> bool:
    """Verify that a dict matches an expected SHA256 hash."""
    return sha256_sign(obj) == expected_hash


# ── JSON Schema Validation ──────────────────────────────────

# SignalEnvelope schema (matches plan R2 §3.2)
SIGNAL_ENVELOPE_SCHEMA = {
    "type": "object",
    "required": ["signal", "confidence", "pair", "timeframe", "reasons", "risks",
                 "model_used", "timestamp", "sha256"],
    "properties": {
        "signal": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD"],
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "pair": {
            "type": "string",
            "pattern": r"^[A-Z]+/[A-Z]+$",
        },
        "timeframe": {
            "type": "string",
            "enum": ["5m", "15m", "1h", "4h"],
        },
        "regime": {
            "type": "string",
            "enum": ["TREND", "RANGE", "ACCUMULATION", "DISTRIBUTION", "PANIC"],
        },
        "ml_verdict": {
            "type": "string",
            "enum": ["PASS", "BLOCK"],
        },
        "ml_probability": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "reasons": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "model_used": {
            "type": "string",
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
        },
        "sha256": {
            "type": "string",
            "pattern": r"^[a-f0-9]{64}$",
        },
    },
    "additionalProperties": False,
}


def validate_json_schema(data: dict, schema: dict) -> tuple[bool, list[str]]:
    """
    Validate data against a JSON Schema.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema)
        return True, []
    except ImportError:
        logger.warning("jsonschema not installed — falling back to manual validation")
        return _manual_validate(data, schema, errors)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema validation error at '{e.path}': {e.message}")
        return False, errors
    except Exception as e:
        errors.append(f"Unexpected validation error: {e}")
        return False, errors


def _manual_validate(data: dict, schema: dict, errors: list) -> tuple[bool, list[str]]:
    """Fallback validation when jsonschema package is not available."""
    if not isinstance(data, dict):
        errors.append("Data must be a JSON object")
        return False, errors

    # Check required fields
    for field in schema.get("required", []):
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Check types
    props = schema.get("properties", {})
    for field, rules in props.items():
        if field not in data:
            continue
        val = data[field]
        expected_type = rules.get("type")

        type_map = {"string": str, "number": (int, float), "array": list, "object": dict}
        if expected_type and expected_type in type_map:
            if not isinstance(val, type_map[expected_type]):
                errors.append(f"Field '{field}' must be {expected_type}, got {type(val).__name__}")

        # Enum check
        if "enum" in rules and val not in rules["enum"]:
            errors.append(f"Field '{field}' must be one of: {rules['enum']}")

        # Number range check
        if expected_type == "number":
            if "minimum" in rules and val < rules["minimum"]:
                errors.append(f"Field '{field}' must be >= {rules['minimum']}")
            if "maximum" in rules and val > rules["maximum"]:
                errors.append(f"Field '{field}' must be <= {rules['maximum']}")

    return len(errors) == 0, errors
