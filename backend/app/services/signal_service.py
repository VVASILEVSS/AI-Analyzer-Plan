"""
AI Analyzer v2.1 — Signal Service (Pipeline Orchestrator)
Coordinates the full signal generation pipeline:
  market_data (Binance) → ML Filter → LLM (LM Studio) → JSON Validator → Regime Detector → Cache → Signal

Includes auto-rotation of signals.jsonl (500 active, rest archived for ML training).
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import (
    CACHE_ENABLED,
    DEFAULT_PAIR,
    DEFAULT_TIMEFRAME,
    OLLAMA_DEFAULT_MODEL,
    SIGNALS_JSONL,
    logger,
)
from app.core.validators import (
    ValidationError,
    build_signal_envelope,
    validate_llm_response,
)
from app.services.cache_service import cache_service
from app.services.injection_blocker import injection_blocker
from app.services.market_data_service import market_data_service
from app.services.ml_filter_service import ml_filter_service
from app.services.ollama_service import ollama_service
from app.services.regime_detector import regime_detector

logger = logging.getLogger("ai_analyzer.signal")

# ── Auto-rotation settings ─────────────────────────────────
MAX_ACTIVE_SIGNALS = 500      # Keep last 500 in signals.jsonl
SIGNALS_ARCHIVE = SIGNALS_JSONL.parent / "signals_archive.jsonl"


class SignalService:
    """Orchestrates the signal generation pipeline."""

    def __init__(self):
        self._signal_count = 0

    async def generate_signal(
        self,
        pair: str = DEFAULT_PAIR,
        timeframe: str = DEFAULT_TIMEFRAME,
        market_data: Optional[dict] = None,
        model: Optional[str] = None,
        force_refresh: bool = False,
    ) -> dict:
        """
        Full pipeline: fetch data → ML filter → LLM → validate → regime → cache → signal.
        """
        start_time = time.time()
        model = model or OLLAMA_DEFAULT_MODEL

        # ── Step 0: Check cache ──────────────────────────────
        request_data = {
            "pair": pair,
            "timeframe": timeframe,
            "model": model,
        }

        if not force_refresh:
            cached = cache_service.get(request_data)
            if cached:
                logger.info(f"Returning cached signal for {pair} ({timeframe})")
                cached["from_cache"] = True
                return cached

        # ── Step 1: Fetch real market data from Binance ──────
        if market_data is None:
            try:
                market_data = await market_data_service.get_market_summary(
                    pair=pair,
                    timeframe=timeframe,
                )
                logger.info(f"Market data fetched for {pair} ({timeframe})")
            except Exception as e:
                logger.warning(f"Failed to fetch market data: {e}")
                market_data = {}

        # ── Step 2: ML Filter ────────────────────────────────
        ml_result = ml_filter_service.predict(market_data or {})
        ml_verdict = ml_result.get("verdict", "PASS")
        ml_probability = ml_result.get("probability", 1.0)

        if ml_result.get("blocked", False):
            logger.warning(f"Signal blocked by ML filter for {pair}")
            blocked_signal = build_signal_envelope(
                signal="HOLD",
                confidence=ml_probability,
                pair=pair,
                timeframe=timeframe,
                reasons=[f"ML-фильтр заблокировал (вероятность={ml_probability:.2f})"],
                risks=["ML-модель определила недостаточное преимущество"],
                model_used=model,
                ml_verdict=ml_verdict,
                ml_probability=ml_probability,
            )
            self._save_signal(blocked_signal)
            return blocked_signal

        # ── Step 3: Build prompt → LLM ───────────────────────
        prompt = self._build_prompt(pair, timeframe, market_data, ml_result)

        injection_check = injection_blocker.check(prompt)
        if not injection_check["safe"]:
            logger.warning(f"Prompt injection detected: {injection_check['threats']}")
            prompt = injection_blocker.sanitize(prompt)

        llm_response = await ollama_service.generate(
            prompt=prompt,
            model=model,
            format="json",
        )

        if not llm_response.get("success"):
            error_msg = llm_response.get("error", "Unknown error")
            logger.error(f"LLM generation failed for {pair}: {error_msg}")
            return {
                "success": False,
                "error": f"Ошибка LLM: {error_msg}",
                "elapsed": time.time() - start_time,
            }

        raw_response = llm_response.get("response", "")
        logger.debug(f"LLM raw response ({len(raw_response)} chars): {raw_response[:200]}")

        # ── Step 4: Parse and validate LLM response ─────────
        try:
            parsed = validate_llm_response(raw_response)
        except ValidationError as e:
            logger.error(f"LLM response validation failed: {e.errors}")
            return {
                "success": False,
                "error": f"Validation error: {e.errors}",
                "elapsed": time.time() - start_time,
            }

        # ── Step 5: Regime Detection ──────────────────────────
        regime_result = regime_detector.detect(market_data or {})
        regime = regime_result.get("regime", "RANGE")

        if market_data and "trend" in market_data:
            md_trend = market_data["trend"]
            regime_map = {"TREND_UP": "TREND", "TREND_DOWN": "TREND", "RANGE": "RANGE", "VOLATILE": "VOLATILE"}
            regime = regime_map.get(md_trend, regime)

        # ── Step 6: Build final SignalEnvelope ──────────────
        signal = build_signal_envelope(
            signal=parsed["signal"],
            confidence=parsed["confidence"],
            pair=pair,
            timeframe=timeframe,
            reasons=parsed.get("reasons", []),
            risks=parsed.get("risks", []),
            model_used=model,
            regime=regime,
            ml_verdict=ml_verdict,
            ml_probability=ml_probability,
        )

        # ── Step 7: Cache result ─────────────────────────────
        cache_service.put(request_data, signal)

        # ── Step 8: Persist to signals.jsonl + auto-rotate ───
        self._save_signal(signal)
        self._rotate_signals()

        self._signal_count += 1
        elapsed = time.time() - start_time

        signal["pipeline"] = {
            "elapsed": round(elapsed, 2),
            "market_data_points": market_data.get("candles_count", 0) if market_data else 0,
            "ml_filter": ml_result,
            "regime": regime_result,
            "llm_elapsed": llm_response.get("elapsed", 0),
            "from_cache": False,
        }

        logger.info(
            f"Signal generated: {signal['signal']} {pair} "
            f"(confidence={signal['confidence']:.2f}, regime={regime}, "
            f"elapsed={elapsed:.1f}s)"
        )

        return signal

    def _build_prompt(
        self,
        pair: str,
        timeframe: str,
        market_data: Optional[dict],
        ml_result: dict,
    ) -> str:
        """Build the LLM prompt from market data and ML filter results."""
        from app.core.config import DEFAULT_PROMPT_TEMPLATE

        market_data_str = "Нет рыночных данных — используй общий анализ."
        if market_data:
            lines = []
            lines.append(f"Текущая цена: {market_data.get('current_price', 'N/A')}")
            lines.append(f"Изменение за 24ч: {market_data.get('24hr_change_pct', 0):.2f}%")
            lines.append(f"Максимум 24ч: {market_data.get('24hr_high', 'N/A')}")
            lines.append(f"Минимум 24ч: {market_data.get('24hr_low', 'N/A')}")
            lines.append(f"Объём 24ч: {market_data.get('24hr_volume', 0):.2f}")
            lines.append(f"Сделки 24ч: {market_data.get('24hr_trades', 0)}")
            lines.append(f"Изменение за окно ({timeframe}): {market_data.get('price_change_window', 0):.2f}%")
            lines.append(f"Последнее изменение: {market_data.get('recent_change', 0):.2f}%")
            lines.append(f"SMA-10: {market_data.get('sma_10', 'N/A')}")
            lines.append(f"SMA-20: {market_data.get('sma_20', 'N/A')}")
            lines.append(f"SMA-50: {market_data.get('sma_50', 'N/A')}")
            lines.append(f"RSI(14): {market_data.get('rsi_14', 'N/A')}")
            lines.append(f"Волатильность: {market_data.get('volatility_pct', 0):.2f}%")
            lines.append(f"Отношение объёма: {market_data.get('volume_ratio', 1):.2f}")
            lines.append(f"Поддержка: {market_data.get('support', 'N/A')}")
            lines.append(f"Сопротивление: {market_data.get('resistance', 'N/A')}")
            lines.append(f"Расстояние от максимума: {market_data.get('distance_from_high_pct', 0):.2f}%")
            lines.append(f"Расстояние от минимума: {market_data.get('distance_from_low_pct', 0):.2f}%")
            lines.append(f"Тренд: {market_data.get('trend', 'N/A')}")
            market_data_str = "\n".join(lines)

        ml_verdict_str = f"{ml_result.get('verdict', 'PASS')} (вероятность={ml_result.get('probability', 1.0):.2f})"
        if ml_result.get('phase'):
            ml_verdict_str += f" [фаза={ml_result['phase']}]"

        return DEFAULT_PROMPT_TEMPLATE.format(
            pair=pair,
            timeframe=timeframe,
            market_data=market_data_str,
            ml_verdict=ml_verdict_str,
            ml_probability=ml_result.get('probability', 1.0),
        )

    def _save_signal(self, signal: dict):
        """Append signal to signals.jsonl file."""
        try:
            SIGNALS_JSONL.parent.mkdir(parents=True, exist_ok=True)
            with open(SIGNALS_JSONL, "a", encoding="utf-8") as f:
                f.write(json.dumps(signal, ensure_ascii=False) + "\n")
        except IOError as e:
            logger.error(f"Failed to save signal to {SIGNALS_JSONL}: {e}")

    def _rotate_signals(self):
        """Auto-rotate: keep last MAX_ACTIVE_SIGNALS, archive the rest."""
        try:
            if not SIGNALS_JSONL.exists():
                return

            with open(SIGNALS_JSONL, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            total = len(lines)

            if total <= MAX_ACTIVE_SIGNALS:
                return

            # Lines to archive (oldest)
            to_archive = lines[:total - MAX_ACTIVE_SIGNALS]
            # Lines to keep (newest)
            to_keep = lines[total - MAX_ACTIVE_SIGNALS:]

            # Write archive
            SIGNALS_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
            with open(SIGNALS_ARCHIVE, "a", encoding="utf-8") as f:
                for line in to_archive:
                    f.write(line + "\n")

            # Rewrite active file
            with open(SIGNALS_JSONL, "w", encoding="utf-8") as f:
                for line in to_keep:
                    f.write(line + "\n")

            logger.info(f"Rotated signals: archived {len(to_archive)}, kept {len(to_keep)}")

        except IOError as e:
            logger.error(f"Signal rotation failed: {e}")

    def get_signals(
        self,
        pair: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Get recent signals from signals.jsonl."""
        signals = []

        if SIGNALS_JSONL.exists():
            try:
                with open(SIGNALS_JSONL, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                sig = json.loads(line)
                                if pair is None or sig.get("pair") == pair.upper():
                                    signals.append(sig)
                            except json.JSONDecodeError:
                                continue

                signals = list(reversed(signals))

            except IOError as e:
                logger.error(f"Failed to read {SIGNALS_JSONL}: {e}")

        total = len(signals)
        page_signals = signals[offset:offset + limit]

        return {
            "signals": page_signals,
            "total": total,
            "page": offset // limit + 1 if limit else 1,
            "per_page": limit,
        }

    def get_stats(self) -> dict:
        """Get signal generation statistics."""
        signals = self.get_signals(limit=1000)
        all_signals = signals["signals"]

        stats = {
            "total_generated": self._signal_count,
            "total_stored": signals["total"],
            "by_signal": {"BUY": 0, "SELL": 0, "HOLD": 0},
            "by_regime": {},
            "avg_confidence": 0,
        }

        if all_signals:
            confidences = [s.get("confidence", 0) for s in all_signals]
            stats["avg_confidence"] = round(sum(confidences) / len(confidences), 4)

            for s in all_signals:
                sig = s.get("signal", "HOLD")
                if sig in stats["by_signal"]:
                    stats["by_signal"][sig] += 1

                regime = s.get("regime", "UNKNOWN")
                stats["by_regime"][regime] = stats["by_regime"].get(regime, 0) + 1

        return stats


# Singleton instance
signal_service = SignalService()
