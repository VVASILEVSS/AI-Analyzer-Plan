"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";
import { Activity, Settings, Brain } from "lucide-react";
import Link from "next/link";

function ConnectionStatus({ health, loading }: { health: HealthResponse | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-dark-card border border-dark-border">
        <div className="w-2.5 h-2.5 rounded-full bg-accent-yellow animate-pulse" />
        <span className="text-sm text-dark-muted">Connecting...</span>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-dark-card border border-accent-red/30">
        <div className="w-2.5 h-2.5 rounded-full bg-accent-red" />
        <span className="text-sm text-accent-red">Disconnected</span>
      </div>
    );
  }

  const connected = health.status === "ok" && health.ollama;
  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full bg-dark-card border ${
        connected ? "border-accent-green/30" : "border-accent-yellow/30"
      }`}
    >
      <div
        className={`w-2.5 h-2.5 rounded-full ${
          connected ? "bg-accent-green status-pulse" : "bg-accent-yellow animate-pulse"
        }`}
      />
      <span className={`text-sm ${connected ? "text-accent-green" : "text-accent-yellow"}`}>
        {connected ? `Ollama: ${health.model}` : "Ollama Offline"}
      </span>
      <span className="text-xs text-dark-muted hidden sm:inline">
        VRAM: {health.vram_tier}
      </span>
    </div>
  );
}

export default function Header() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await api.health();
        setHealth(data);
      } catch {
        setHealth(null);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-dark-border bg-dark-bg/95 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left: Logo & Title */}
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="p-2 rounded-lg bg-accent-green/10">
              <Brain className="w-5 h-5 text-accent-green" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-dark-text tracking-tight">
                AI Analyzer
              </h1>
              <p className="text-xs text-dark-muted -mt-0.5">v2.1 — локальный сигнальный движок</p>
            </div>
          </Link>

          {/* Right: Status & Nav */}
          <div className="flex items-center gap-3">
            <ConnectionStatus health={health} loading={loading} />
            <Link
              href="/settings"
              className="p-2 rounded-lg text-dark-muted hover:text-dark-text hover:bg-dark-hover transition-colors"
              title="Settings"
            >
              <Settings className="w-4.5 h-4.5" />
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
