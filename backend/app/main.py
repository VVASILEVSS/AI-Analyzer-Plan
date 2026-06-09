"""
AI Analyzer v2.1 — FastAPI Main Entry
Application startup with Watchdog, CORS, and route registration.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import API_HOST, API_PORT, DEBUG, logger
from app.core.watchdog import watchdog
from app.api.endpoints.signals import router as signals_router

# ── Lifespan (startup/shutdown) ─────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start watchdog on startup, stop on shutdown."""
    logger.info("Starting AI Analyzer v2.1...")

    # Initialize ML filter (try to load model)
    from app.services.ml_filter_service import ml_filter_service
    if ml_filter_service.is_loaded:
        logger.info("ML filter model loaded successfully")
    else:
        logger.warning("ML filter model not found — filter will pass through all signals")

    # Initialize security (Fernet key)
    from app.core.security import init_fernet
    init_fernet()

    # Start watchdog
    await watchdog.start()

    logger.info(f"AI Analyzer v2.1 started on {API_HOST}:{API_PORT}")
    yield

    # Shutdown
    logger.info("Shutting down AI Analyzer v2.1...")
    await watchdog.stop()

    # Flush cache
    from app.services.cache_service import cache_service
    cache_service.flush()


# ── App ─────────────────────────────────────────────────────

app = FastAPI(
    title="AI Analyzer v2.1",
    description="LOCAL AI ENGINE — Crypto trading signal analyzer powered by local LLM (Ollama)",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
)

# CORS — allow Next.js frontend (default: localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(signals_router)

# Root redirect
@app.get("/")
async def root():
    return {
        "name": "AI Analyzer v2.1",
        "version": "2.1.0",
        "docs": "/docs" if DEBUG else "disabled",
        "api": "/api/v1",
    }


# ── Run directly ───────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info",
    )
