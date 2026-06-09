"use client";

import type { SignalEnvelope, SignalType } from "@/lib/types";
import { ArrowUpDown, ArrowUpRight, ArrowDownRight, Minus, Clock } from "lucide-react";

function signalColor(type: SignalType) {
  switch (type) {
    case "BUY": return "text-accent-green";
    case "SELL": return "text-accent-red";
    case "HOLD": return "text-accent-gray";
  }
}

function SignalIcon({ type }: { type: SignalType }) {
  switch (type) {
    case "BUY": return <ArrowUpRight className="w-3.5 h-3.5" />;
    case "SELL": return <ArrowDownRight className="w-3.5 h-3.5" />;
    case "HOLD": return <Minus className="w-3.5 h-3.5" />;
  }
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleString("ru-RU", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return ts;
  }
}

export default function SignalHistory({ signals }: { signals: SignalEnvelope[] }) {
  if (signals.length === 0) {
    return (
      <div className="rounded-xl border border-dark-border bg-dark-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <ArrowUpDown className="w-5 h-5 text-dark-muted" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-dark-muted">
            История сигналов
          </h2>
        </div>
        <div className="text-center py-8 text-dark-muted text-sm">
          Нет сигналов в истории
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-dark-border bg-dark-card overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-dark-border">
        <ArrowUpDown className="w-5 h-5 text-dark-muted" />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-dark-muted">
          История сигналов
        </h2>
        <span className="text-xs text-dark-muted ml-auto">
          {signals.length} сигнал{signals.length !== 1 ? "ов" : ""}
        </span>
      </div>

      <div className="max-h-96 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-dark-surface">
            <tr className="border-b border-dark-border text-xs uppercase tracking-wider text-dark-muted">
              <th className="text-left px-5 py-2.5 font-medium">Сигнал</th>
              <th className="text-left px-3 py-2.5 font-medium">Пара</th>
              <th className="text-left px-3 py-2.5 font-medium hidden sm:table-cell">Таймфрейм</th>
              <th className="text-left px-3 py-2.5 font-medium">Достоверность</th>
              <th className="text-left px-3 py-2.5 font-medium hidden md:table-cell">Режим</th>
              <th className="text-left px-3 py-2.5 font-medium hidden lg:table-cell">Модель</th>
              <th className="text-right px-5 py-2.5 font-medium">Время</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((sig, i) => (
              <tr
                key={`${sig.sha256}-${i}`}
                className="border-b border-dark-border/50 hover:bg-dark-hover transition-colors"
              >
                <td className="px-5 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className={signalColor(sig.signal)}>
                      <SignalIcon type={sig.signal} />
                    </span>
                    <span className={`font-semibold ${signalColor(sig.signal)}`}>
                      {sig.signal}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2.5 text-dark-text font-medium">{sig.pair}</td>
                <td className="px-3 py-2.5 text-dark-muted hidden sm:table-cell">
                  {sig.timeframe}
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-dark-bg overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          sig.signal === "BUY"
                            ? "bg-accent-green"
                            : sig.signal === "SELL"
                              ? "bg-accent-red"
                              : "bg-accent-gray"
                        }`}
                        style={{ width: `${Math.round(sig.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-dark-muted">
                      {Math.round(sig.confidence * 100)}%
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2.5 hidden md:table-cell">
                  {sig.regime ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-dark-bg text-dark-muted border border-dark-border">
                      {sig.regime}
                    </span>
                  ) : (
                    <span className="text-xs text-dark-muted">—</span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-xs text-dark-muted font-mono hidden lg:table-cell truncate max-w-[120px]">
                  {sig.model_used}
                </td>
                <td className="px-5 py-2.5 text-right">
                  <div className="flex items-center justify-end gap-1 text-xs text-dark-muted">
                    <Clock className="w-3 h-3" />
                    {formatTimestamp(sig.timestamp)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
