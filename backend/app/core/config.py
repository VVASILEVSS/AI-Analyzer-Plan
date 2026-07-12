"""
AI Analyzer v2.1 — Configuration
Central config for FastAPI, Ollama, GPU/VRAM, paths.
"""

import os
import json
from pathlib import Path
from typing import Optional, Literal

# ── Base paths ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
APP_DIR = BASE_DIR / "app"
DATA_DIR = APP_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"
CONFIG_DIR = APP_DIR / "config"

# Ensure directories exist
for d in [DATA_DIR, LOGS_DIR, MODELS_DIR, CONFIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Data files ──────────────────────────────────────────────
SIGNALS_JSONL = DATA_DIR / "signals.jsonl"
CACHE_SHA256 = DATA_DIR / "cache_sha256.json"
PROMPT_TEMPLATES = CONFIG_DIR / "prompt_templates.json"
PAIR_TOKEN_MAP = CONFIG_DIR / "pair_token_map.json"
SIGNALS_LOG = LOGS_DIR / "signals.log"
ML_FILTER_PKL = MODELS_DIR / "ml_filter_v1.pkl"

# ── FastAPI ─────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
API_PREFIX: str = "/api/v1"
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

# ── Ollama ──────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:1234")
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # seconds
OLLAMA_DEFAULT_MODEL: str = os.getenv(
    "OLLAMA_DEFAULT_MODEL", "qwen_qwen2.5-vl-7b-instruct"
)
# API key for cloud OpenAI-compatible endpoints (Alibaba GLM, OpenRouter, etc.)
# When empty — works with local Ollama/LM Studio without auth.
OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")

# ── GPU / VRAM ──────────────────────────────────────────────
# "auto" tries to detect via nvidia-smi; fallback to MANUAL_VRAM_GB
GPU_DETECTION: Literal["auto", "manual"] = os.getenv("GPU_DETECTION", "auto")
MANUAL_VRAM_GB: int = int(os.getenv("MANUAL_VRAM_GB", "8"))

# VRAM tiers from plan R2
VRAM_LOW = 8       # 1 model 7B only
VRAM_MID = 12      # 2 models alternating (7B + 9B)
VRAM_HIGH = 16     # 2-3 models simultaneously


def detect_vram_gb() -> int:
    """Try to detect VRAM via nvidia-smi. Returns 0 on failure."""
    import subprocess
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Take first GPU
            line = result.stdout.strip().split("\n")[0].strip()
            return int(float(line) / 1024)  # MiB -> GiB (approx)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return 0


def get_vram_tier() -> str:
    """Return 'low', 'mid', or 'high' based on detected/manual VRAM."""
    if GPU_DETECTION == "auto":
        vram = detect_vram_gb()
        if vram == 0:
            vram = MANUAL_VRAM_GB
    else:
        vram = MANUAL_VRAM_GB

    if vram < 10:
        return "low"
    elif vram < 14:
        return "mid"
    else:
        return "high"


def get_max_concurrent_models() -> int:
    """Max models that can run simultaneously based on VRAM tier."""
    tier = get_vram_tier()
    return {"low": 1, "mid": 1, "high": 3}[tier]


# ── Models available ────────────────────────────────────────
MODELS = {
    "primary": {
        "name": "qwen_qwen2.5-vl-7b-instruct",
        "size_gb": 4.5,
        "task": "signal_analysis",
    },
    "secondary": {
        "name": "glm4:9b-q4_K_M",       # Stage 2
        "size_gb": 5.8,
        "task": "signal_analysis",
        "available": False,              # Enable in Stage 2
    },
    "deep": {
        "name": "deepseek-r1:8b",         # v2.2
        "size_gb": 5.0,
        "task": "deep_analysis",
        "available": False,
    },
}

# ── ML Filter ───────────────────────────────────────────────
ML_FILTER_ENABLED: bool = os.getenv("ML_FILTER_ENABLED", "true").lower() == "true"
ML_FILTER_PHASE: Literal["log_only", "active"] = os.getenv(
    "ML_FILTER_PHASE", "log_only"
)
ML_FILTER_BLOCK_THRESHOLD: float = float(os.getenv("ML_FILTER_BLOCK_THRESHOLD", "0.5"))
ML_MODEL_PATH: str = os.getenv("ML_MODEL_PATH", str(ML_FILTER_PKL))

# ── Security ────────────────────────────────────────────────
FERNET_KEY: Optional[str] = os.getenv("FERNET_KEY")  # If None, encryption disabled

# ── Cache ───────────────────────────────────────────────────
CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "4"))

# ── Signal settings ────────────────────────────────────────
DEFAULT_PAIR: str = "BTC/USDT"
DEFAULT_TIMEFRAME: str = "1h"
SIGNAL_CONFIDENCE_MIN: float = 0.3  # Below this → force HOLD
SIGNAL_CONFIDENCE_LOW: float = 0.6   # Below this → flag as low confidence

# ── Logging ─────────────────────────────────────────────────
import logging

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(SIGNALS_LOG, encoding="utf-8"),
    ],
)
logger = logging.getLogger("ai_analyzer")

# ── Prompt templates (defaults) ────────────────────────────
DEFAULT_PROMPT_TEMPLATE = """Ты — профессиональный аналитик криптовалютных рынков. 
Проанализируй данные и выдай торговый сигнал.

Рыночные данные для {pair} ({timeframe}):
{market_data}

Вердикт ML-фильтра: {ml_verdict}
Вероятность ML-фильтра: {ml_probability:.2f}

Ответь ТОЛЬКО валидным JSON:
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "reasons": ["причина 1", "причина 2"],
  "risks": ["риск 1", "риск 2"]
}}

Правила:
- signal: BUY, SELL или HOLD
- confidence: число от 0 до 100 (проценты)
- reasons: 2-4 причины на русском языке, ссылайся на данные
- risks: 1-3 предупреждения на русском языке
- Ответь ТОЛЬКО JSON, без markdown, без комментариев"""