"use client";

import type { SignalEnvelope, SignalType } from "@/lib/types";
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  ShieldCheck,
  ShieldX,
  Hash,
  Clock,
  Cpu,
  AlertTriangle,
} from "lucide-react";

function signalColor(type: SignalType) {
  switch (type) {
    case "BUY":
      return {
        bg: "bg-accent-green/10",
        border: "border-accent-green/30",
        text: "text-accent-green",
        bar: "bg-accent-green",
        glow: "shadow-accent-green/20",
      };
    case "SELL":
      return {
        bg: "bg-accent-red/10",
        border: "border-accent-red/30",
        text: "text-accent-red",
        bar: "bg-accent-red",
        glow: "shadow-accent-red/20",
      };
    case "HOLD":
      return {
        bg: "bg-accent-gray/10",
        border: "border-accent-gray/30",
        text: "text-accent-gray",
        bar: "bg-accent-gray",
        glow: "shadow-accent-gray/20",
      };
  }
}

function SignalIcon({ type }: { type: SignalType }) {
  const color = signalColor(type);
  switch (type) {
    case "BUY":
      return <TrendingUp className={`w-10 h-10 ${color.text}`} />;
    case "SELL":
      return <TrendingDown className={`w-10 h-10 ${color.text}`} />;
    case "HOLD":
      return <Minus className={`w-10 h-10 ${color.text}`} />;
  }
}

function RegimeBadge({ regime }: { regime?: string }) {
  if (!regime) return null;
  const colors: Record<string, string> = {
    TREND: "bg-accent-green/10 text-accent-green border-accent-green/30",
    RANGE: "bg-accent-blue/10 text-accent-blue border-accent-blue/30",
    ACCUMULATION: "bg-accent-yellow/10 text-accent-yellow border-accent-yellow/30",
    PANIC: "bg-accent-red/10 text-accent-red border-accent-red/30",
  };
  const colorClass = colors[regime] || "bg-dark-card text-dark-muted border-dark-border";
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {regime}
    </span>
  );
}

function MLVerdictBadge({ verdict }: { verdict?: string }) {
  if (!verdict) return null;
  if (verdict === "PASS") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-green/10 text-accent-green border border-accent-green/30">
        <ShieldCheck className="w-3 h-3" />
        {verdict}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-red/10 text-accent-red border border-accent-red/30">
      <ShieldX className="w-3 h-3" />
      {verdict}
    </span>
  );
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleString("ru-RU", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return ts;
  }
}

export default function SignalCard({ signal }: { signal: SignalEnvelope | null }) {
  if (!signal) {
    return (
      <div className="rounded-xl border border-dark-border bg-dark-card p-6">
        <div className="flex flex-col items-center justify-center py-12 text-dark-muted">
          <Activity className="w-12 h-12 mb-3 opacity-40" />
          <p className="text-sm">Сигнал ещё не сгенерирован</p>
          <p className="text-xs mt-1 opacity-60">Нажмите «Получить Сигнал», чтобы проанализировать торговую пару</p>
        </div>
      </div>
    );
  }

  const colors = signalColor(signal.signal);
  const confidencePercent = Math.min(100, Math.max(0, Math.round(signal.confidence * 100)));

  return (
    <div className={`rounded-xl border ${colors.border} bg-dark-card shadow-lg ${colors.glow} overflow-hidden`}>
      {/* Top signal banner */}
      <div className={`flex items-center justify-between px-6 py-4 ${colors.bg}`}>
        <div className="flex items-center gap-3">
          <SignalIcon type={signal.signal} />
          <div>
            <div className={`text-2xl font-bold tracking-tight ${colors.text}`}>
              {signal.signal}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm font-medium text-dark-text">{signal.pair}</span>
              <span className="text-xs text-dark-muted">|</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-dark-bg/50 text-dark-muted border border-dark-border">
                <Clock className="w-3 h-3" />
                {signal.timeframe}
              </span>
            </div>
          </div>
        </div>
        {signal.from_cache && (
          <span className="text-xs px-2 py-1 rounded bg-dark-bg/50 text-dark-muted border border-dark-border">
            ИЗ КЭША
          </span>
        )}
      </div>

      <div className="px-6 py-5 space-y-5">
        {/* Confidence bar */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium uppercase tracking-wider text-dark-muted">
              Уверенность
            </span>
            <span className={`text-lg font-bold ${colors.text}`}>{confidencePercent}%</span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-dark-bg overflow-hidden">
            <div
              className={`h-full rounded-full confidence-fill ${colors.bar}`}
              style={{ "--bar-width": `${confidencePercent}%` } as React.CSSProperties}
            />
          </div>
        </div>

        {/* Badges row */}
        <div className="flex flex-wrap items-center gap-2">
          <RegimeBadge regime={signal.regime} />
          <MLVerdictBadge verdict={signal.ml_verdict} />
          {signal.ml_probability !== undefined && (
            <span className="text-xs text-dark-muted">
              ML вер.: {(signal.ml_probability * 100).toFixed(1)}%
            </span>
          )}
        </div>

        {/* Reasons */}
        {signal.reasons.length > 0 && (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-wider text-dark-muted mb-2">
              Причины
            </h4>
            <ul className="space-y-1.5">
              {signal.reasons.map((reason, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-dark-text"
                >
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent-green shrink-0" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Risks */}
        {signal.risks.length > 0 && (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-wider text-dark-muted mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3" />
              Риски
            </h4>
            <ul className="space-y-1.5">
              {signal.risks.map((risk, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-dark-text"
                >
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent-red shrink-0" />
                  {risk}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Footer metadata */}
        <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-dark-border text-xs text-dark-muted">
          <div className="flex items-center gap-1">
            <Cpu className="w-3.5 h-3.5" />
            <span>{signal.model_used}</span>
          </div>
          <div className="flex items-center gap-1">
            <Hash className="w-3.5 h-3.5" />
            <span className="font-mono">{signal.sha256.slice(0, 8)}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            <span>{formatTimestamp(signal.timestamp)}</span>
          </div>
          {signal.pipeline && (
            <span>
              Сгенерировано за {signal.pipeline.elapsed.toFixed(1)}с
              {signal.pipeline.llm_elapsed > 0 &&
                ` (LLM: ${signal.pipeline.llm_elapsed.toFixed(1)}с)`}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
