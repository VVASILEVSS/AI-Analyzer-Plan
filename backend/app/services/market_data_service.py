"""
AI Analyzer v2.1 — Market Data Service
Fetches real-time OHLCV data from Binance public API.
Includes symbol search and autocomplete (SPOT + FUTURES).
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger("ai_analyzer.market_data")

# Binance API
BINANCE_BASE_URL = "https://api.binance.com"
BINANCE_FUTURES_URL = "https://fapi.binance.com"
BINANCE_KLINES = "/api/v3/klines"
BINANCE_24HR = "/api/v3/ticker/24hr"
BINANCE_PRICE = "/api/v3/ticker/price"
BINANCE_EXCHANGE_INFO = "/api/v3/exchangeInfo"
BINANCE_FUTURES_EXCHANGE_INFO = "/fapi/v1/exchangeInfo"

# Timeframe mapping for Binance interval parameter
TIMEFRAME_MAP = {
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

# How many candles to fetch
DEFAULT_LIMIT = 50

# Cache for exchange symbols (loaded once)
_cached_spot_symbols: Optional[list[str]] = None
_cached_futures_symbols: Optional[list[str]] = None


class MarketDataService:
    """Fetches market data from Binance with symbol search (spot + futures)."""

    def __init__(self, base_url: str = BINANCE_BASE_URL):
        self.base_url = base_url
        self.timeout = 15

    # ── Symbol search & autocomplete (SPOT + FUTURES) ────

    async def _load_spot_symbols(self) -> list[str]:
        """Load all active spot symbols from Binance."""
        global _cached_spot_symbols
        if _cached_spot_symbols is not None:
            return _cached_spot_symbols

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BINANCE_BASE_URL}{BINANCE_EXCHANGE_INFO}",
                )
                if resp.status_code == 200:
                    data = resp.json()
                    _cached_spot_symbols = [
                        s["symbol"] for s in data.get("symbols", [])
                        if s.get("status") == "TRADING"
                    ]
                    logger.info(f"Loaded {len(_cached_spot_symbols)} Binance spot symbols")
                else:
                    _cached_spot_symbols = []
        except Exception as e:
            logger.error(f"Failed to load Binance spot symbols: {e}")
            _cached_spot_symbols = []

        return _cached_spot_symbols

    async def _load_futures_symbols(self) -> list[str]:
        """Load all active futures symbols from Binance Futures."""
        global _cached_futures_symbols
        if _cached_futures_symbols is not None:
            return _cached_futures_symbols

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BINANCE_FUTURES_URL}{BINANCE_FUTURES_EXCHANGE_INFO}",
                )
                if resp.status_code == 200:
                    data = resp.json()
                    _cached_futures_symbols = [
                        s["symbol"] for s in data.get("symbols", [])
                        if s.get("status") == "TRADING"
                        and s.get("contractType") != "PERPETUAL"
                    ]
                    # Also add perpetuals (USDT-M)
                    perpetuals = [
                        s["symbol"] for s in data.get("symbols", [])
                        if s.get("status") == "TRADING"
                        and s.get("contractType") == "PERPETUAL"
                        and s.get("symbol", "").endswith("USDT")
                    ]
                    # Remove perpetuals that are duplicates of quarterly
                    perp_set = set(perpetuals)
                    _cached_futures_symbols = list(set(_cached_futures_symbols) | perp_set)
                    logger.info(f"Loaded {len(_cached_futures_symbols)} Binance futures symbols")
                else:
                    _cached_futures_symbols = []
        except Exception as e:
            logger.error(f"Failed to load Binance futures symbols: {e}")
            _cached_futures_symbols = []

        return _cached_futures_symbols

    async def search_symbols(
        self, query: str, limit: int = 20
    ) -> list[dict]:
        """
        Search Binance symbols (spot + futures) by query.
        Returns list of {"symbol": "BTC/USDT", "type": "SPOT"} objects.
        Supports partial match (e.g. "BTC" -> "BTC/USDT" SPOT, "BTCUSDT" FUTURES).
        """
        import asyncio

        if not query or len(query) < 1:
            return []

        clean_query = query.upper().replace("/", "").replace("-", "").replace("_", "")

        # Load both symbol lists in parallel
        spot_task = self._load_spot_symbols()
        futures_task = self._load_futures_symbols()
        spot_syms, futures_syms = await asyncio.gather(spot_task, futures_task)

        # ── Search spot: prioritize USDT pairs ─────────────
        spot_usdt = [
            s for s in spot_syms
            if clean_query in s and s.endswith("USDT")
        ]
        spot_other = [
            s for s in spot_syms
            if clean_query in s and not s.endswith("USDT")
            and s.endswith(("BUSD", "BTC", "ETH", "BNB", "EUR", "TRY", "BRL"))
        ]

        # ── Search futures: prioritize USDT perpetuals ────
        futures_usdt = [
            s for s in futures_syms
            if clean_query in s and s.endswith("USDT")
        ]
        futures_other = [
            s for s in futures_syms
            if clean_query in s and not s.endswith("USDT")
        ]

        # ── Build results with type info ──────────────────
        results = []
        seen = set()

        def add_result(raw_symbol: str, sym_type: str, priority: int):
            """Format symbol and add to results (skip duplicates)."""
            if raw_symbol in seen:
                return
            seen.add(raw_symbol)

            # Format: insert "/" before last known quote asset
            formatted = _format_pair(raw_symbol)
            results.append({
                "symbol": formatted,
                "type": sym_type,
                "priority": priority,
            })

        # Priority: starts-with spot USDT > starts-with futures USDT > contains spot > contains futures

        # Spot USDT (starts with query)
        for s in spot_usdt:
            if s.startswith(clean_query):
                add_result(s, "SPOT", 1)
        # Futures USDT (starts with query)
        for s in futures_usdt:
            if s.startswith(clean_query):
                add_result(s, "FUTURES", 2)
        # Spot USDT (contains query)
        for s in spot_usdt:
            if not s.startswith(clean_query):
                add_result(s, "SPOT", 3)
        # Futures USDT (contains query)
        for s in futures_usdt:
            if not s.startswith(clean_query):
                add_result(s, "FUTURES", 4)
        # Spot other quotes
        for s in spot_other:
            add_result(s, "SPOT", 5)
        # Futures other
        for s in futures_other:
            add_result(s, "FUTURES", 6)

        # Sort by priority and take limit
        results.sort(key=lambda x: x["priority"])
        results = results[:limit]

        # Remove priority key from output
        for r in results:
            del r["priority"]

        return results

    # ── Klines (candlestick data) ─────────────────────────

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = DEFAULT_LIMIT,
    ) -> Optional[list[dict]]:
        """Fetch OHLCV candlestick data from Binance."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}{BINANCE_KLINES}",
                    params={
                        "symbol": symbol,
                        "interval": interval,
                        "limit": limit,
                    },
                )

                if resp.status_code != 200:
                    logger.error(f"Binance klines error {resp.status_code}: {resp.text[:200]}")
                    return None

                data = resp.json()
                candles = []

                for k in data:
                    candles.append({
                        "open_time": k[0],
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "close_time": k[6],
                        "quote_volume": float(k[7]),
                        "trades": k[8],
                    })

                logger.info(f"Fetched {len(candles)} candles for {symbol} ({interval})")
                return candles

        except httpx.TimeoutException:
            logger.error("Binance API timeout")
            return None
        except Exception as e:
            logger.error(f"Binance klines fetch error: {e}")
            return None

    # ── 24hr ticker ────────────────────────────────────────

    async def get_24hr_ticker(self, symbol: str) -> Optional[dict]:
        """Fetch 24hr ticker statistics."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}{BINANCE_24HR}",
                    params={"symbol": symbol},
                )

                if resp.status_code != 200:
                    return None

                data = resp.json()
                return {
                    "price_change": float(data.get("priceChange", 0)),
                    "price_change_pct": float(data.get("priceChangePercent", 0)),
                    "high": float(data.get("highPrice", 0)),
                    "low": float(data.get("lowPrice", 0)),
                    "volume": float(data.get("volume", 0)),
                    "quote_volume": float(data.get("quoteAssetVolume", 0)),
                    "trades": int(data.get("count", 0)),
                    "weighted_avg": float(data.get("weightedAvgPrice", 0)),
                }

        except Exception as e:
            logger.error(f"Binance 24hr ticker error: {e}")
            return None

    # ── Price ──────────────────────────────────────────────

    async def get_price(self, symbol: str) -> Optional[float]:
        """Get latest price."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}{BINANCE_PRICE}",
                    params={"symbol": symbol},
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return float(data.get("price", 0))
        except Exception:
            pass
        return None

    # ── Market summary for signal generation ──────────────

    async def get_market_summary(
        self,
        pair: str,
        timeframe: str,
    ) -> dict:
        """
        Get comprehensive market data for signal generation.
        pair: e.g. "BTC/USDT" or "BTCUSDT"
        """
        symbol = pair.replace("/", "")
        interval = TIMEFRAME_MAP.get(timeframe, "1h")

        import asyncio

        klines_task = self.get_klines(symbol, interval, limit=50)
        ticker_task = self.get_24hr_ticker(symbol)

        results = await asyncio.gather(klines_task, ticker_task, return_exceptions=True)

        candles = results[0] if isinstance(results[0], list) else []
        ticker = results[1] if isinstance(results[1], dict) else {}

        analysis = self._analyze_candles(candles, timeframe)

        summary = {
            "pair": pair,
            "timeframe": timeframe,
            "current_price": candles[-1]["close"] if candles else 0,
            "24hr_change_pct": ticker.get("price_change_pct", 0),
            "24hr_high": ticker.get("high", 0),
            "24hr_low": ticker.get("low", 0),
            "24hr_volume": ticker.get("volume", 0),
            "24hr_trades": ticker.get("trades", 0),
            "candles_count": len(candles),
        }

        summary.update(analysis)

        logger.info(f"Market summary for {pair}: price={summary['current_price']}, "
                     f"change_24h={summary['24hr_change_pct']:.2f}%")

        return summary

    # ── Technical analysis ────────────────────────────────

    def _analyze_candles(self, candles: list[dict], timeframe: str) -> dict:
        """Calculate basic technical indicators from candle data."""
        if not candles:
            return {"error": "No candle data available"}

        closes = [c["close"] for c in candles]
        volumes = [c["volume"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        current = closes[-1]
        prev = closes[-2] if len(closes) > 1 else current

        window_change = ((current - closes[0]) / closes[0]) * 100 if closes[0] != 0 else 0
        recent_change = ((current - prev) / prev) * 100 if prev != 0 else 0

        sma_10 = sum(closes[-10:]) / min(10, len(closes)) if closes else 0
        sma_20 = sum(closes[-20:]) / min(20, len(closes)) if len(closes) >= 5 else 0
        sma_50 = sum(closes[-50:]) / min(50, len(candles)) if len(candles) >= 5 else 0

        volatility = 0
        if len(closes) >= 5:
            mean = sum(closes[-20:]) / min(20, len(closes))
            variance = sum((x - mean) ** 2 for x in closes[-20:]) / min(20, len(closes))
            volatility = (variance ** 0.5 / mean) * 100 if mean != 0 else 0

        rsi = 50
        if len(closes) >= 15:
            gains, losses = [], []
            for i in range(1, min(15, len(closes))):
                diff = closes[-i] - closes[-i - 1]
                gains.append(diff if diff > 0 else 0)
                losses.append(-diff if diff < 0 else 0)
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0.001
            rs = avg_gain / avg_loss if avg_loss != 0 else 100
            rsi = 100 - (100 / (1 + rs))

        avg_volume = sum(volumes[-20:]) / min(20, len(volumes)) if volumes else 0
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1.0

        highest = max(highs)
        lowest = min(lows)
        distance_from_high = ((highest - current) / highest) * 100 if highest != 0 else 0
        distance_from_low = ((current - lowest) / lowest) * 100 if lowest != 0 else 0

        support = min(lows[-20:]) if len(lows) >= 5 else lowest
        resistance = max(highs[-20:]) if len(highs) >= 5 else highest

        trend = "RANGE"
        if sma_10 > sma_20 and recent_change > 0.5:
            trend = "TREND_UP"
        elif sma_10 < sma_20 and recent_change < -0.5:
            trend = "TREND_DOWN"
        elif abs(recent_change) > 2:
            trend = "VOLATILE"

        return {
            "price_change_window": round(window_change, 2),
            "recent_change": round(recent_change, 2),
            "sma_10": round(sma_10, 2),
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "volatility_pct": round(volatility, 2),
            "rsi_14": round(rsi, 1),
            "volume_ratio": round(volume_ratio, 2),
            "avg_volume": round(avg_volume, 2),
            "current_volume": round(volumes[-1], 2),
            "highest": round(highest, 2),
            "lowest": round(lowest, 2),
            "distance_from_high_pct": round(distance_from_high, 2),
            "distance_from_low_pct": round(distance_from_low, 2),
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "trend": trend,
        }


# ── Helper: format raw symbol to "BASE/QUOTE" ───────────

_KNOWN_QUOTES = [
    "USDT", "BUSD", "USDC", "TUSD", "DAI", "FDUSD",
    "BTC", "ETH", "BNB", "EUR", "GBP", "TRY", "BRL", "ARS",
    "USD", "NGN", "UAH", "RUB", "ZAR", "INR",
]

def _format_pair(raw_symbol: str) -> str:
    """Convert 'BTCUSDT' to 'BTC/USDT' using known quote assets."""
    for quote in _KNOWN_QUOTES:
        if raw_symbol.endswith(quote):
            base = raw_symbol[:-len(quote)]
            if base:
                return f"{base}/{quote}"
    # Fallback: split at 3-4 chars from end
    if len(raw_symbol) > 5:
        return f"{raw_symbol[:-4]}/{raw_symbol[-4:]}"
    return raw_symbol


# Singleton
market_data_service = MarketDataService()
