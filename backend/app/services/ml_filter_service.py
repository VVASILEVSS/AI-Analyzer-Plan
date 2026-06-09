"""
AI Analyzer v2.1 — ML Filter Service
Random Forest classifier extracted from v1 ollama_client.py.
50 features, AUC=0.842 on 211 labeled samples.

Phase 1A: log_only — filter runs but doesn't block signals
Phase 1B: active — filter blocks weak signals below threshold
"""

import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import (
    ML_FILTER_BLOCK_THRESHOLD,
    ML_FILTER_ENABLED,
    ML_FILTER_PHASE,
    ML_MODEL_PATH,
    logger,
)

logger = logging.getLogger("ai_analyzer.ml_filter")


class MLFilterService:
    """ML-based pre-filter for market data before LLM analysis."""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path or ML_MODEL_PATH)
        self._model = None
        self._loaded = False
        self._phase = ML_FILTER_PHASE
        self._enabled = ML_FILTER_ENABLED

    # ── Model loading ───────────────────────────────────────

    def load_model(self) -> bool:
        """Load the Random Forest model from .pkl file."""
        if not self.model_path.exists():
            logger.warning(
                f"ML model not found at {self.model_path}. "
                "ML filter will be disabled. Retrain with 211 labeled samples."
            )
            return False

        try:
            with open(self.model_path, "rb") as f:
                self._model = pickle.load(f)
            self._loaded = True
            logger.info(f"ML model loaded from {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready."""
        if not self._loaded and self._enabled:
            self.load_model()
        return self._loaded

    @property
    def is_active(self) -> bool:
        """Check if filter is in active (blocking) phase."""
        return self._enabled and self._loaded and self._phase == "active"

    def set_phase(self, phase: str):
        """Switch between 'log_only' and 'active' phases."""
        if phase not in ("log_only", "active"):
            raise ValueError(f"Invalid phase: {phase}. Must be 'log_only' or 'active'")
        self._phase = phase
        logger.info(f"ML filter phase set to: {phase}")

    # ── Feature extraction ─────────────────────────────────

    @staticmethod
    def extract_features(market_data: dict) -> Optional[np.ndarray]:
        """
        Extract 50 features from market data for the ML model.
        Features match v1 training data format.

        Expected market_data keys (OHLCV-based):
        - open, high, low, close, volume
        - rsi, macd, macd_signal, macd_hist
        - bb_upper, bb_middle, bb_lower, bb_width
        - ema_9, ema_21, ema_50
        - oi (open interest)
        - cvd (cumulative volume delta)
        - funding_rate
        - volatility
        - price_change_pct
        - volume_change_pct
        - etc.
        """
        features = []

        try:
            # Price features (1-10)
            features.append(market_data.get("close", 0))
            features.append(market_data.get("open", 0))
            features.append(market_data.get("high", 0))
            features.append(market_data.get("low", 0))
            features.append(market_data.get("volume", 0))

            # Price changes (11-15)
            close = market_data.get("close", 0)
            open_price = market_data.get("open", 0)
            features.append((close - open_price) / open_price if open_price else 0)
            features.append(market_data.get("price_change_pct", 0))
            features.append(market_data.get("volume_change_pct", 0))
            features.append(
                (market_data.get("high", 0) - market_data.get("low", 0)) / close
                if close else 0
            )
            features.append(market_data.get("volatility", 0))

            # Technical indicators (16-30)
            features.append(market_data.get("rsi", 50))
            features.append(market_data.get("macd", 0))
            features.append(market_data.get("macd_signal", 0))
            features.append(market_data.get("macd_hist", 0))
            features.append(market_data.get("bb_upper", 0))
            features.append(market_data.get("bb_middle", 0))
            features.append(market_data.get("bb_lower", 0))
            features.append(market_data.get("bb_width", 0))
            features.append(market_data.get("ema_9", 0))
            features.append(market_data.get("ema_21", 0))
            features.append(market_data.get("ema_50", 0))
            features.append(market_data.get("atr", 0))
            features.append(market_data.get("adx", 0))
            features.append(market_data.get("obv", 0))
            features.append(market_data.get("vwap", 0))

            # Derivatives / ratios (31-40)
            features.append(market_data.get("oi", 0))
            features.append(market_data.get("oi_change_pct", 0))
            features.append(market_data.get("cvd", 0))
            features.append(market_data.get("funding_rate", 0))
            features.append(market_data.get("long_short_ratio", 0))
            features.append(
                market_data.get("close", 0) / market_data.get("vwap", 1)
                if market_data.get("vwap") else 1
            )
            features.append(
                market_data.get("close", 0) / market_data.get("ema_21", 1)
                if market_data.get("ema_21") else 1
            )
            features.append(
                (market_data.get("close", 0) - market_data.get("bb_lower", 0))
                / (market_data.get("bb_upper", 0) - market_data.get("bb_lower", 0) + 1e-10)
            )
            features.append(
                market_data.get("volume", 0) / market_data.get("volume_ma", 1)
                if market_data.get("volume_ma") else 1
            )
            features.append(market_data.get("momentum", 0))

            # Time-based (41-50)
            import time
            features.append(market_data.get("hour_of_day", time.localtime().tm_hour))
            features.append(market_data.get("day_of_week", time.localtime().tm_wday))
            features.append(market_data.get("is_weekend", 0))
            features.append(market_data.get("session", 0))  # 0=asia, 1=eu, 2=us
            features.append(market_data.get("trend_1h", 0))
            features.append(market_data.get("trend_4h", 0))
            features.append(market_data.get("trend_1d", 0))
            features.append(market_data.get("support_dist_pct", 0))
            features.append(market_data.get("resistance_dist_pct", 0))
            features.append(market_data.get("liquidation_risk", 0))

            # Pad to exactly 50 features if needed
            while len(features) < 50:
                features.append(0.0)

            return np.array(features[:50], dtype=np.float32)

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    # ── Prediction ──────────────────────────────────────────

    def predict(self, market_data: dict) -> dict:
        """
        Run ML filter on market data. Returns verdict and probability.
        """
        if not self._enabled:
            return {"verdict": "PASS", "probability": 1.0, "blocked": False, "phase": "disabled"}

        if not self.is_loaded:
            # Model not available — pass through
            return {"verdict": "PASS", "probability": 1.0, "blocked": False, "phase": "unloaded"}

        features = self.extract_features(market_data)
        if features is None:
            logger.warning("Feature extraction returned None — passing through")
            return {"verdict": "PASS", "probability": 1.0, "blocked": False, "phase": self._phase}

        try:
            probability = float(self._model.predict_proba(features.reshape(1, -1))[0][1])
            prediction = self._model.predict(features.reshape(1, -1))[0]
            verdict = "BLOCK" if prediction == 0 else "PASS"

            # In log_only phase, never block
            blocked = self._phase == "active" and verdict == "BLOCK" and probability < ML_FILTER_BLOCK_THRESHOLD

            result = {
                "verdict": verdict,
                "probability": round(probability, 4),
                "blocked": blocked,
                "phase": self._phase,
                "features_count": len(features),
            }

            if blocked:
                logger.warning(
                    f"ML filter BLOCKED signal (probability={probability:.2f}, "
                    f"threshold={ML_FILTER_BLOCK_THRESHOLD})"
                )
            else:
                logger.info(
                    f"ML filter verdict={verdict} (probability={probability:.2f}, phase={self._phase})"
                )

            return result

        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return {"verdict": "PASS", "probability": 1.0, "blocked": False, "phase": self._phase, "error": str(e)}


# Singleton instance
ml_filter_service = MLFilterService()
