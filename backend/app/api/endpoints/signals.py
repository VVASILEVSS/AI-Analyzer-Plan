"""
AI Analyzer v2.1 — API Endpoints: Signals
POST /api/v1/signal  — Generate a new signal
GET /api/v1/signals  — List recent signals
GET /api/v1/signals/{sha256} — Get specific signal
GET /api/v1/health  — Health check
GET /api/v1/stats   — Signal statistics
GET /api/v1/models  — Available Ollama models
GET /api/v1/search-symbols — Search Binance pairs (spot + futures) with autocomplete
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.validators import ValidationError
from app.models.signal_envelope import (
    HealthResponse,
    SignalEnvelope,
    SignalRequest,
)
from app.services.ollama_service import ollama_service
from app.services.signal_service import signal_service

logger = logging.getLogger("ai_analyzer.api")

router = APIRouter(prefix="/api/v1", tags=["signals"])


# ── Health ─────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health: API, Ollama, watchdog status."""
    ollama_ok = await ollama_service.health_check()

    from app.core.config import OLLAMA_DEFAULT_MODEL, get_vram_tier
    from app.core.watchdog import watchdog

    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama=ollama_ok,
        model=OLLAMA_DEFAULT_MODEL if ollama_ok else None,
        vram_tier=get_vram_tier(),
        watchdog=watchdog.get_status(),
    )


# ── Generate Signal ────────────────────────────────────────

@router.post("/signal")
async def generate_signal(request: SignalRequest):
    """
    Generate a new trading signal.
    Full pipeline: ML Filter → Ollama → JSON Validate → Regime → Cache.
    """
    logger.info(f"Signal request: {request.pair} ({request.timeframe}), force={request.force_refresh}")

    result = await signal_service.generate_signal(
        pair=request.pair,
        timeframe=request.timeframe,
        market_data=request.market_data,
        force_refresh=request.force_refresh,
    )

    if not result.get("success", True):
        raise HTTPException(
            status_code=502,
            detail=result.get("error", "Signal generation failed"),
        )

    return result


# ── List Signals ────────────────────────────────────────────

@router.get("/signals")
async def list_signals(
    pair: Optional[str] = Query(None, description="Filter by trading pair"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get recent signals from history."""
    return signal_service.get_signals(pair=pair, limit=limit, offset=offset)


# ── Get Signal by SHA256 ────────────────────────────────────

@router.get("/signals/{sha256}")
async def get_signal(sha256: str):
    """Get a specific signal by its SHA256 hash."""
    signals = signal_service.get_signals(limit=10000)
    for sig in signals["signals"]:
        if sig.get("sha256") == sha256:
            return sig
    raise HTTPException(status_code=404, detail=f"Signal with SHA256 {sha256} not found")


# ── Statistics ──────────────────────────────────────────────

@router.get("/stats")
async def signal_stats():
    """Get signal generation statistics."""
    return signal_service.get_stats()


# ── Available Models ────────────────────────────────────────

@router.get("/models")
async def list_models():
    """List available Ollama models."""
    models = await ollama_service.list_models()
    from app.core.config import get_vram_tier, MODELS, OLLAMA_DEFAULT_MODEL

    return {
        "available": [
            {
                "name": m.get("name", ""),
                "size": m.get("size", 0),
                "modified": m.get("modified_at", ""),
            }
            for m in models
        ],
        "configured": MODELS,
        "default": OLLAMA_DEFAULT_MODEL,
        "vram_tier": get_vram_tier(),
    }


# ── Binance Symbol Search (SPOT + FUTURES) ──────────────────

@router.get("/search-symbols")
async def search_symbols(
    q: str = Query("", min_length=1, description="Search query (e.g. BTC, ETH)"),
    limit: int = Query(20, ge=1, le=50, description="Max results to return"),
):
    """
    Search Binance trading pairs (spot + futures) with autocomplete.
    Returns list of {"symbol": "BTC/USDT", "type": "SPOT"} objects.
    Results are sorted by relevance: starts-with > contains, USDT > other quotes.
    """
    from app.services.market_data_service import market_data_service

    results = await market_data_service.search_symbols(q, limit=limit)
    return {"symbols": results, "query": q}


# ── Cache Management ───────────────────────────────────────

@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return signal_service.get_stats()  # Temp: return signal stats
    # from app.services.cache_service import cache_service
    # return cache_service.stats()


@router.post("/cache/clear")
async def cache_clear():
    """Clear expired cache entries."""
    from app.services.cache_service import cache_service
    cache_service.clear_expired()
    return {"status": "ok", "message": "Expired entries cleared"}
