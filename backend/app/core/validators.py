"""
AI Analyzer v2.1 — SignalEnvelope Validators
JSON Schema validation for the unified signal format.
New module for v2 — ensures all pipeline outputs conform to SignalEnvelope.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import (
    SIGNAL_CONFIDENCE_MIN,
    SIGNAL_CONFIDENCE_LOW,
    logger,
)
from app.core.security import (
    SIGNAL_ENVELOPE_SCHEMA,
    sha256_sign,
    validate_json_schema,
)

# Valid values
VALID_SIGNALS = {"BUY", "SELL", "HOLD"}
VALID_TIMEFRAMES = {"5m", "15m", "1h", "4h"}
VALID_REGIMES = {"TREND", "RANGE", "ACCUMULATION", "DISTRIBUTION", "PANIC"}
VALID_ML_VERDICTS = {"PASS", "BLOCK"}


class ValidationError(Exception):
    """Raised when signal validation fails."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Signal validation failed: {'; '.join(errors)}")


def validate_signal_envelope(data: dict) -> dict:
    """
    Full validation of a SignalEnvelope against the schema.
    Returns cleaned/normalized data.
    Raises ValidationError on failure.
    """
    errors = []

    # 1. Schema validation
    is_valid, schema_errors = validate_json_schema(data, SIGNAL_ENVELOPE_SCHEMA)
    if not is_valid:
        errors.extend(schema_errors)

    # 2. Signal-specific validation
    signal = data.get("signal", "").upper()
    if signal not in VALID_SIGNALS:
        errors.append(f"Invalid signal: '{signal}'. Must be one of: {VALID_SIGNALS}")

    # 3. Confidence bounds
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        errors.append(f"Confidence must be 0.0-1.0, got: {confidence}")

    # 4. Pair format
    pair = data.get("pair", "")
    if "/" not in pair or len(pair.split("/")) != 2:
        errors.append(f"Invalid pair format: '{pair}'. Expected 'BASE/QUOTE'")

    # 5. Timeframe
    timeframe = data.get("timeframe", "")
    if timeframe not in VALID_TIMEFRAMES:
        errors.append(f"Invalid timeframe: '{timeframe}'. Must be one of: {VALID_TIMEFRAMES}")

    # 6. Regime (optional in Stage 1)
    regime = data.get("regime")
    if regime and regime not in VALID_REGIMES:
        errors.append(f"Invalid regime: '{regime}'. Must be one of: {VALID_REGIMES}")

    # 7. Reasons must be non-empty
    reasons = data.get("reasons", [])
    if not isinstance(reasons, list) or len(reasons) == 0:
        errors.append("Signal must have at least 1 reason")

    # 8. Risks (optional but should be list)
    risks = data.get("risks", [])
    if not isinstance(risks, list):
        errors.append("Risks must be an array")

    # 9. Model used
    model_used = data.get("model_used", "")
    if not model_used:
        errors.append("model_used is required")

    # 10. Timestamp format
    timestamp = data.get("timestamp", "")
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                errors.append("Timestamp must include timezone (ISO 8601)")
        except (ValueError, AttributeError):
            errors.append(f"Invalid timestamp format: '{timestamp}'. Expected ISO 8601")

    # 11. SHA256 verification (if present)
    sha256 = data.get("sha256", "")
    if sha256:
        expected = sha256_sign(data)
        # Compare without sha256 field itself (it's self-referential)
        data_without_hash = {k: v for k, v in data.items() if k != "sha256"}
        expected = sha256_sign(data_without_hash)
        if sha256 != expected:
            errors.append("SHA256 hash mismatch — data may have been tampered with")

    if errors:
        raise ValidationError(errors)

    # Normalize data
    return _normalize_envelope(data)


def _normalize_envelope(data: dict) -> dict:
    """Normalize and clean a SignalEnvelope."""
    normalized = {
        "signal": data["signal"].upper(),
        "confidence": round(float(data["confidence"]), 4),
        "pair": data["pair"].upper(),
        "timeframe": data["timeframe"],
        "reasons": [str(r) for r in data.get("reasons", [])],
        "risks": [str(r) for r in data.get("risks", [])],
        "model_used": data.get("model_used", ""),
        "timestamp": data.get("timestamp", ""),
        "sha256": data.get("sha256", ""),
    }

    # Optional fields
    for field in ["regime", "ml_verdict", "ml_probability"]:
        if field in data and data[field] is not None:
            normalized[field] = data[field]

    return normalized


def build_signal_envelope(
    signal: str,
    confidence: float,
    pair: str,
    timeframe: str,
    reasons: list[str],
    risks: list[str],
    model_used: str,
    regime: Optional[str] = None,
    ml_verdict: Optional[str] = None,
    ml_probability: Optional[float] = None,
) -> dict:
    """
    Build a complete, valid SignalEnvelope with auto-generated timestamp and SHA256.
    """
    from app.core.security import sha256_sign

    # Force low-confidence signals to HOLD
    if confidence < SIGNAL_CONFIDENCE_MIN:
        signal = "HOLD"
        reasons = [f"Confidence {confidence:.2f} below minimum threshold {SIGNAL_CONFIDENCE_MIN}"] + reasons

    timestamp = datetime.now(timezone.utc).isoformat()

    envelope = {
        "signal": signal.upper(),
        "confidence": round(confidence, 4),
        "pair": pair.upper(),
        "timeframe": timeframe,
        "reasons": reasons,
        "risks": risks,
        "model_used": model_used,
        "timestamp": timestamp,
    }

    if regime:
        envelope["regime"] = regime
    if ml_verdict:
        envelope["ml_verdict"] = ml_verdict
    if ml_probability is not None:
        envelope["ml_probability"] = round(ml_probability, 4)

    # Compute SHA256 hash
    envelope["sha256"] = sha256_sign(envelope)

    return envelope


def validate_llm_response(raw_response: str) -> dict:
    """
    Parse and validate an LLM raw response string into a SignalEnvelope partial.
    The LLM should return a JSON object. This function extracts and validates it.
    Returns partial dict with: signal, confidence, reasons, risks
    Raises ValidationError if parsing fails.
    """
    import json
    import re

    errors = []

    # Try to extract JSON from the response
    # LLMs sometimes wrap JSON in ```json ... ``` blocks or add text around it
    json_str = raw_response.strip()

    # Remove markdown code blocks
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", json_str, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()

    # Try to find JSON object
    if not json_str.startswith("{"):
        # Try to find first { and last }
        start = json_str.find("{")
        end = json_str.rfind("}")
        if start != -1 and end != -1:
            json_str = json_str[start:end + 1]

    # Parse JSON
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        errors.append(f"Failed to parse JSON from LLM response: {e}")
        errors.append(f"Raw response: {raw_response[:200]}")
        raise ValidationError(errors)

    if not isinstance(parsed, dict):
        errors.append(f"LLM response is not a JSON object, got: {type(parsed).__name__}")
        raise ValidationError(errors)

    # Validate required fields for partial signal
    required = ["signal", "confidence"]
    for field in required:
        if field not in parsed:
            errors.append(f"Missing field in LLM response: {field}")

    if errors:
        raise ValidationError(errors)

    # Validate signal value
    sig = parsed.get("signal", "").upper()
    if sig not in VALID_SIGNALS:
        errors.append(f"Invalid signal in LLM response: '{sig}'")
        raise ValidationError(errors)

    # Validate confidence
    conf = parsed.get("confidence", 0)
    if not isinstance(conf, (int, float)) or not (0 <= conf <= 100):
        errors.append(f"Invalid confidence: {conf}")
        raise ValidationError(errors)

    return {
        "signal": sig,
        "confidence": float(conf) / 100,
        "reasons": [str(r) for r in parsed.get("reasons", [])],
        "risks": [str(r) for r in parsed.get("risks", [])],
    }
