"""
AI Analyzer v2.1 — Regime Detector
Market phase detection: TREND / RANGE / ACCUMULATION / DISTRIBUTION / PANIC
New module for v2.1 (partially existed as regime_score in v1 OHLCV processing).
"""

import logging
from typing import Optional

from app.core.config import logger

logger = logging.getLogger("ai_analyzer.regime")


class RegimeDetector:
    """
    Detects market regime based on OHLCV data and technical indicators.
    Uses simple heuristics — can be enhanced with ML in future stages.
    """

    # Regime thresholds (tunable via config in future)
    THRESHOLDS = {
        "volatility_high": 0.03,      # >3% range = high volatility
        "volatility_panic": 0.06,      # >6% range = panic
        "trend_adx_strong": 25,        # ADX > 25 = trending
        "volume_spike": 2.0,           # Volume > 2x average = spike
        "bb_squeeze": 0.01,            # BB width < 1% = squeeze (accumulation)
        "trend_consistency": 0.6,      # % of candles in trend direction
    }

    def detect(self, market_data: dict) -> dict:
        """
        Detect market regime from market data dict.
        Returns: {"regime": str, "confidence": float, "indicators": dict}
        """
        indicators = self._extract_indicators(market_data)
        regime, confidence = self._classify(indicators)

        return {
            "regime": regime,
            "confidence": round(confidence, 4),
            "indicators": indicators,
        }

    def _extract_indicators(self, data: dict) -> dict:
        """Extract regime-relevant indicators from market data."""
        close = data.get("close", 0)
        open_price = data.get("open", 0)
        high = data.get("high", 0)
        low = data.get("low", 0)
        volume = data.get("volume", 0)

        indicators = {
            "price_range_pct": (high - low) / close if close else 0,
            "body_ratio": abs(close - open_price) / (high - low + 1e-10),
            "candle_direction": 1 if close > open_price else (-1 if close < open_price else 0),
            "volume_ratio": volume / data.get("volume_ma", volume + 1),
            "rsi": data.get("rsi", 50),
            "adx": data.get("adx", 0),
            "bb_width": data.get("bb_width", 0),
            "atr": data.get("atr", 0),
            "ema_9": data.get("ema_9", close),
            "ema_21": data.get("ema_21", close),
            "ema_50": data.get("ema_50", close),
            "macd_hist": data.get("macd_hist", 0),
            "funding_rate": data.get("funding_rate", 0),
            "oi_change_pct": data.get("oi_change_pct", 0),
        }

        # Derived indicators
        indicators["price_vs_ema21"] = (close - indicators["ema_21"]) / indicators["ema_21"] if indicators["ema_21"] else 0
        indicators["trend_alignment"] = 1 if indicators["ema_9"] > indicators["ema_21"] > indicators["ema_50"] else (
            -1 if indicators["ema_9"] < indicators["ema_21"] < indicators["ema_50"] else 0
        )

        return indicators

    def _classify(self, indicators: dict) -> tuple[str, float]:
        """
        Classify market regime based on indicators.
        Returns (regime_name, confidence).
        """
        scores = {
            "TREND": 0.0,
            "RANGE": 0.0,
            "ACCUMULATION": 0.0,
            "DISTRIBUTION": 0.0,
            "PANIC": 0.0,
        }

        # ── Panic detection (highest priority) ───────────────
        vol = indicators.get("price_range_pct", 0)
        if vol > self.THRESHOLDS["volatility_panic"]:
            scores["PANIC"] += 4.0
        elif vol > self.THRESHOLDS["volatility_high"]:
            scores["PANIC"] += 1.5

        # Volume spike + high volatility = panic
        if indicators.get("volume_ratio", 0) > self.THRESHOLDS["volume_spike"] and vol > self.THRESHOLDS["volatility_high"]:
            scores["PANIC"] += 2.0

        # Extreme funding + OI drop = panic
        if abs(indicators.get("funding_rate", 0)) > 0.001 and indicators.get("oi_change_pct", 0) < -0.1:
            scores["PANIC"] += 2.0

        # ── Trend detection ──────────────────────────────────
        adx = indicators.get("adx", 0)
        if adx > self.THRESHOLDS["trend_adx_strong"]:
            scores["TREND"] += 2.5
        elif adx > 15:
            scores["TREND"] += 1.0

        # EMA alignment
        alignment = indicators.get("trend_alignment", 0)
        if alignment == 1:
            scores["TREND"] += 2.0
            scores["ACCUMULATION"] += 0.5
        elif alignment == -1:
            scores["TREND"] += 2.0
            scores["DISTRIBUTION"] += 0.5

        # MACD histogram direction
        if indicators.get("macd_hist", 0) > 0:
            scores["TREND"] += 1.0
        elif indicators.get("macd_hist", 0) < 0:
            scores["TREND"] += 0.5

        # RSI extremes
        rsi = indicators.get("rsi", 50)
        if rsi > 70:
            scores["TREND"] += 0.5
            scores["DISTRIBUTION"] += 0.5  # Overbought = potential distribution
        elif rsi < 30:
            scores["TREND"] += 0.5
            scores["ACCUMULATION"] += 0.5  # Oversold = potential accumulation

        # ── Range detection ─────────────────────────────────
        if vol < self.THRESHOLDS["volatility_high"] * 0.5:
            scores["RANGE"] += 2.0
        if adx < 15:
            scores["RANGE"] += 1.5
        if indicators.get("body_ratio", 0) < 0.3:
            scores["RANGE"] += 1.0  # Doji/small body = indecision

        # ── Accumulation / Distribution ───────────────────────
        bb_width = indicators.get("bb_width", 0)
        if bb_width < self.THRESHOLDS["bb_squeeze"]:
            scores["ACCUMULATION"] += 2.0  # BB squeeze = potential breakout
            scores["RANGE"] += 1.0

        price_vs_ema = indicators.get("price_vs_ema21", 0)
        if price_vs_ema > 0.01 and indicators.get("volume_ratio", 0) < 0.8:
            scores["ACCUMULATION"] += 1.0  # Price up on low volume = institutional accumulation
        elif price_vs_ema < -0.01 and indicators.get("volume_ratio", 0) < 0.8:
            scores["DISTRIBUTION"] += 1.0  # Price down on low volume = distribution

        # ── Select regime with highest score ────────────────
        max_regime = max(scores, key=scores.get)
        total_score = sum(scores.values())
        confidence = scores[max_regime] / total_score if total_score > 0 else 0.2

        return max_regime, min(confidence, 1.0)


# Singleton instance
regime_detector = RegimeDetector()
