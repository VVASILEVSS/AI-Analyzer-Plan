"""
AI Analyzer v2.1 — SignalEnvelope Data Model
Pydantic model for type-safe signal handling.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class SignalEnvelope(BaseModel):
    """Unified signal format — all modules communicate via this schema (Plan R2 §3.2)."""

    signal: str = Field(..., description="BUY / SELL / HOLD")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Signal confidence 0.0-1.0")
    pair: str = Field(..., description="Trading pair, e.g. BTC/USDT")
    timeframe: str = Field(..., description="5m / 15m / 1h / 4h")
    reasons: list[str] = Field(..., min_length=1, description="Reasons for the signal")
    risks: list[str] = Field(default_factory=list, description="Identified risks")
    model_used: str = Field(..., description="Model that generated the signal")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    sha256: str = Field(..., description="SHA256 hash for caching")

    # Optional fields (added during pipeline)
    regime: Optional[str] = Field(None, description="TREND / RANGE / ACCUMULATION / DISTRIBUTION / PANIC")
    ml_verdict: Optional[str] = Field(None, description="PASS / BLOCK")
    ml_probability: Optional[float] = Field(None, description="ML filter probability score")

    @validator("signal")
    def validate_signal(cls, v):
        v = v.upper()
        if v not in {"BUY", "SELL", "HOLD"}:
            raise ValueError(f"Invalid signal: {v}. Must be BUY, SELL, or HOLD")
        return v

    @validator("pair")
    def validate_pair(cls, v):
        v = v.upper()
        if "/" not in v:
            raise ValueError(f"Invalid pair format: {v}. Expected BASE/QUOTE")
        return v

    @validator("timeframe")
    def validate_timeframe(cls, v):
        if v not in {"5m", "15m", "1h", "4h"}:
            raise ValueError(f"Invalid timeframe: {v}. Must be 5m, 15m, 1h, or 4h")
        return v

    @validator("regime")
    def validate_regime(cls, v):
        if v is not None and v not in {"TREND", "RANGE", "ACCUMULATION", "DISTRIBUTION", "PANIC"}:
            raise ValueError(f"Invalid regime: {v}")
        return v

    @validator("ml_verdict")
    def validate_ml_verdict(cls, v):
        if v is not None and v not in {"PASS", "BLOCK"}:
            raise ValueError(f"Invalid ML verdict: {v}. Must be PASS or BLOCK")
        return v

    @validator("sha256")
    def validate_sha256(cls, v):
        import re
        if not re.match(r"^[a-f0-9]{64}$", v):
            raise ValueError("SHA256 must be a 64-character hex string")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "signal": "BUY",
                "confidence": 0.78,
                "pair": "BTC/USDT",
                "timeframe": "1h",
                "regime": "TREND",
                "ml_verdict": "PASS",
                "ml_probability": 0.82,
                "reasons": ["OI growing steadily", "CVD bullish divergence", "Price above VWAP"],
                "risks": ["Price near liquidation level at 68000", "RSI overbought on 4h"],
                "model_used": "qwen2.5-vl:7b-instruct-q4_K_M",
                "timestamp": "2026-06-08T12:00:00Z",
                "sha256": "abc123...64chars",
            }
        }


class SignalRequest(BaseModel):
    """Request body for generating a new signal."""

    pair: str = Field(default="BTC/USDT", description="Trading pair")
    timeframe: str = Field(default="1h", description="Timeframe")
    market_data: Optional[dict] = Field(None, description="Optional market data to analyze")
    force_refresh: bool = Field(False, description="Ignore cache and generate new signal")


class SignalListResponse(BaseModel):
    """Response for listing signals."""

    signals: list[SignalEnvelope]
    total: int
    page: int = 1
    per_page: int = 20


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    ollama: bool
    model: Optional[str] = None
    vram_tier: Optional[str] = None
    watchdog: Optional[dict] = None
