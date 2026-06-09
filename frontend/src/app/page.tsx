"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { SignalEnvelope, SignalStats } from "@/lib/types";
import SignalCard from "@/components/SignalCard";
import SignalHistory from "@/components/SignalHistory";
import StatsPanel from "@/components/StatsPanel";
import { Zap, RefreshCw, Loader2, ChevronDown, Search } from "lucide-react";

const POPULAR_PAIRS = [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
  "BNB/USDT",
  "XRP/USDT",
  "ADA/USDT",
  "DOGE/USDT",
  "AVAX/USDT",
  "DOT/USDT",
  "LINK/USDT",
];

const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

interface SymbolResult {
  symbol: string;
  type: "SPOT" | "FUTURES";
}

export default function Dashboard() {
  const [currentSignal, setCurrentSignal] = useState<SignalEnvelope | null>(null);
  const [signalHistory, setSignalHistory] = useState<SignalEnvelope[]>([]);
  const [stats, setStats] = useState<SignalStats | null>(null);
  const [selectedPair, setSelectedPair] = useState("BTC/USDT");
  const [selectedTimeframe, setSelectedTimeframe] = useState("1h");
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pairDropdownOpen, setPairDropdownOpen] = useState(false);
  const [tfDropdownOpen, setTfDropdownOpen] = useState(false);

  // Pair search
  const [pairSearch, setPairSearch] = useState("");
  const [pairSuggestions, setPairSuggestions] = useState<SymbolResult[]>([]);
  const [searchingPairs, setSearchingPairs] = useState(false);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Close dropdown on click outside
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setPairDropdownOpen(false);
        setTfDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Search Binance symbols with debounce
  const searchBinancePairs = useCallback(async (query: string) => {
    if (!query || query.length < 1) {
      setPairSuggestions([]);
      return;
    }

    setSearchingPairs(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/search-symbols?q=${encodeURIComponent(query)}&limit=15`
      );
      if (res.ok) {
        const data = await res.json();
        setPairSuggestions(data.symbols || []);
      }
    } catch {
      // ignore
    } finally {
      setSearchingPairs(false);
    }
  }, []);

  const handlePairSearchChange = (value: string) => {
    setPairSearch(value);
    setPairDropdownOpen(true);

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (value.length >= 1) {
      searchTimeoutRef.current = setTimeout(() => {
        searchBinancePairs(value);
      }, 300);
    } else {
      setPairSuggestions([]);
    }
  };

  const selectPair = (pair: string) => {
    setSelectedPair(pair);
    setPairSearch("");
    setPairSuggestions([]);
    setPairDropdownOpen(false);
  };

  // Filter popular pairs by search
  const filteredPopular = pairSearch
    ? POPULAR_PAIRS.filter(p => p.toUpperCase().includes(pairSearch.toUpperCase()))
    : POPULAR_PAIRS;

  const fetchInitialData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [signalsRes, statsRes] = await Promise.allSettled([
        api.signals(1, 20),
        api.stats(),
      ]);

      if (signalsRes.status === "fulfilled") {
        const data = signalsRes.value;
        setSignalHistory(data.signals);
        if (data.signals.length > 0) {
          setCurrentSignal(data.signals[0]);
        }
      }

      if (statsRes.status === "fulfilled") {
        setStats(statsRes.value);
      }

      if (signalsRes.status === "rejected" && statsRes.status === "rejected") {
        setError("Нет подключения к бэкенду. Убедитесь что сервер запущен на порту 8000.");
      }
    } catch {
      setError("Не удалось загрузить данные.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  const handleGenerateSignal = async () => {
    setGenerating(true);
    setError(null);
    try {
      const signal = await api.generateSignal({
        pair: selectedPair,
        timeframe: selectedTimeframe,
        force_refresh: true,
      });
      setCurrentSignal(signal);
      setSignalHistory((prev) => [signal, ...prev].slice(0, 20));

      try {
        const newStats = await api.stats();
        setStats(newStats);
      } catch {
        // stats refresh failure is non-critical
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сгенерировать сигнал");
    } finally {
      setGenerating(false);
    }
  };

  const handleRefreshHistory = async () => {
    try {
      const data = await api.signals(1, 20);
      setSignalHistory(data.signals);
      if (data.signals.length > 0 && !currentSignal) {
        setCurrentSignal(data.signals[0]);
      }
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3 text-dark-muted">
          <Loader2 className="w-8 h-8 animate-spin" />
          <p className="text-sm">Загрузка панели...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-accent-red/30 bg-accent-red/5 px-4 py-3 text-sm text-accent-red">
          {error}
        </div>
      )}

      {/* Top row: Signal Card + Generate Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Signal Card - takes 2 columns */}
        <div className="lg:col-span-2">
          <SignalCard signal={currentSignal} />
        </div>

        {/* Generate Signal Controls */}
        <div className="space-y-4">
          {/* Pair selector with search */}
          <div className="rounded-xl border border-dark-border bg-dark-card p-4 space-y-3">
            <label className="block text-xs font-medium uppercase tracking-wider text-dark-muted">
              ТОРГОВАЯ ПАРА
            </label>
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => {
                  setPairDropdownOpen(!pairDropdownOpen);
                  setTfDropdownOpen(false);
                }}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-dark-bg border border-dark-border text-dark-text text-sm hover:border-dark-hover transition-colors"
              >
                <span>{selectedPair}</span>
                <ChevronDown className={`w-4 h-4 text-dark-muted transition-transform ${pairDropdownOpen ? "rotate-180" : ""}`} />
              </button>
              {pairDropdownOpen && (
                <div className="absolute z-20 top-full mt-1 w-full rounded-lg bg-dark-surface border border-dark-border shadow-xl overflow-hidden">
                  {/* Search input */}
                  <div className="p-2 border-b border-dark-border">
                    <div className="relative">
                      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-dark-muted" />
                      <input
                        type="text"
                        value={pairSearch}
                        onChange={(e) => handlePairSearchChange(e.target.value)}
                        placeholder="Поиск тикера (BTC, ETH...)"
                        className="w-full pl-8 pr-3 py-1.5 rounded bg-dark-bg border border-dark-border text-dark-text text-xs placeholder:text-dark-muted/50 focus:outline-none focus:border-accent-green/50"
                        autoFocus
                      />
                    </div>
                  </div>

                  {/* Suggestions list */}
                  <div className="max-h-64 overflow-y-auto">
                    {searchingPairs && (
                      <div className="px-3 py-2 text-xs text-dark-muted">Поиск...</div>
                    )}

                    {/* Binance search results (spot + futures) */}
                    {pairSuggestions.length > 0 && pairSearch.length >= 1 && (
                      <>
                        <div className="px-3 py-1 text-xs text-dark-muted/60 uppercase tracking-wider">
                          Результаты Binance
                        </div>
                        {pairSuggestions.slice(0, 15).map((item) => (
                          <button
                            key={`${item.symbol}-${item.type}`}
                            onClick={() => selectPair(item.symbol)}
                            className={`w-full text-left px-3 py-1.5 text-xs hover:bg-dark-hover transition-colors flex items-center justify-between ${
                              item.symbol === selectedPair ? "text-accent-green bg-accent-green/5" : "text-dark-text"
                            }`}
                          >
                            <span className="font-mono">{item.symbol}</span>
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                item.type === "FUTURES"
                                  ? "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30"
                                  : "bg-green-500/15 text-green-400 border border-green-500/30"
                              }`}
                            >
                              {item.type === "FUTURES" ? "ФЬЮЧЕРС" : "СПОТ"}
                            </span>
                          </button>
                        ))}
                      </>
                    )}

                    {/* Popular pairs (fallback / always shown when no search) */}
                    {(!pairSearch || filteredPopular.length > 0) && (
                      <>
                        {pairSearch && pairSuggestions.length > 0 && (
                          <div className="border-t border-dark-border/50 mx-2" />
                        )}
                        <div className="px-3 py-1 text-xs text-dark-muted/60 uppercase tracking-wider">
                          Популярные
                        </div>
                        {filteredPopular.map((pair) => (
                          <button
                            key={pair}
                            onClick={() => selectPair(pair)}
                            className={`w-full text-left px-3 py-1.5 text-xs hover:bg-dark-hover transition-colors ${
                              pair === selectedPair ? "text-accent-green bg-accent-green/5" : "text-dark-text"
                            }`}
                          >
                            <span className="font-mono">{pair}</span>
                          </button>
                        ))}
                      </>
                    )}

                    {pairSearch && pairSuggestions.length === 0 && filteredPopular.length === 0 && (
                      <div className="px-3 py-3 text-xs text-dark-muted text-center">
                        Ничего не найдено
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Timeframe selector */}
          <div className="rounded-xl border border-dark-border bg-dark-card p-4 space-y-3">
            <label className="block text-xs font-medium uppercase tracking-wider text-dark-muted">
              ВРЕМЕННЫЕ РАМКИ
            </label>
            <div className="relative">
              <button
                onClick={() => {
                  setTfDropdownOpen(!tfDropdownOpen);
                  setPairDropdownOpen(false);
                }}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-dark-bg border border-dark-border text-dark-text text-sm hover:border-dark-hover transition-colors"
              >
                <span>{selectedTimeframe}</span>
                <ChevronDown className={`w-4 h-4 text-dark-muted transition-transform ${tfDropdownOpen ? "rotate-180" : ""}`} />
              </button>
              {tfDropdownOpen && (
                <div className="absolute z-20 top-full mt-1 w-full rounded-lg bg-dark-surface border border-dark-border shadow-xl overflow-hidden">
                  {TIMEFRAMES.map((tf) => (
                    <button
                      key={tf}
                      onClick={() => {
                        setSelectedTimeframe(tf);
                        setTfDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-dark-hover transition-colors ${
                        tf === selectedTimeframe ? "text-accent-green bg-accent-green/5" : "text-dark-text"
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerateSignal}
            disabled={generating}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-accent-green hover:bg-accent-green/90 disabled:opacity-50 disabled:cursor-not-allowed text-dark-bg font-semibold text-sm transition-colors shadow-lg shadow-accent-green/20"
          >
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Генерация...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Получить Сигнал
              </>
            )}
          </button>
        </div>
      </div>

      {/* Stats Panel */}
      <StatsPanel stats={stats} />

      {/* Signal History */}
      <div className="flex items-center justify-end">
        <button
          onClick={handleRefreshHistory}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-dark-muted hover:text-dark-text hover:bg-dark-hover transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Обновить
        </button>
      </div>
      <SignalHistory signals={signalHistory} />
    </div>
  );
}
