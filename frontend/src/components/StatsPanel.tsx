"use client";

import type { SignalStats } from "@/lib/types";
import { BarChart3, TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";

function StatCard({
  label,
  value,
  icon,
  color,
  subtext,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  subtext?: string;
}) {
  return (
    <div className="rounded-xl border border-dark-border bg-dark-card p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-dark-muted">
          {label}
        </span>
        <span className={color}>{icon}</span>
      </div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      {subtext && <span className="text-xs text-dark-muted">{subtext}</span>}
    </div>
  );
}

export default function StatsPanel({ stats }: { stats: SignalStats | null }) {
  if (!stats) {
    return (
      <div className="rounded-xl border border-dark-border bg-dark-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-dark-muted" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-dark-muted">
            Статистика
          </h2>
        </div>
        <div className="text-center py-6 text-dark-muted text-sm">
          Статистика недоступна
        </div>
      </div>
    );
  }

  const buyCount = stats.by_signal?.BUY ?? 0;
  const sellCount = stats.by_signal?.SELL ?? 0;
  const holdCount = stats.by_signal?.HOLD ?? 0;
  const total = stats.total_generated || 1;
  const avgConf = Math.round((stats.avg_confidence ?? 0) * 100);

  return (
    <div className="rounded-xl border border-dark-border bg-dark-card overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-dark-border">
        <BarChart3 className="w-5 h-5 text-dark-muted" />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-dark-muted">
          Статистика
        </h2>
      </div>
      <div className="p-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Всего сигналов"
          value={stats.total_generated}
          icon={<Activity className="w-5 h-5" />}
          color="text-dark-text"
          subtext={`Средняя достоверность: ${avgConf}%`}
        />
        <StatCard
          label="Сигналы на покупку"
          value={buyCount}
          icon={<TrendingUp className="w-5 h-5" />}
          color="text-accent-green"
          subtext={`${((buyCount / total) * 100).toFixed(0)}% от всех`}
        />
        <StatCard
          label="Сигналы на продажу"
          value={sellCount}
          icon={<TrendingDown className="w-5 h-5" />}
          color="text-accent-red"
          subtext={`${((sellCount / total) * 100).toFixed(0)}% от всех`}
        />
        <StatCard
          label="Сигналы удержания"
          value={holdCount}
          icon={<Minus className="w-5 h-5" />}
          color="text-accent-gray"
          subtext={`${((holdCount / total) * 100).toFixed(0)}% от всех`}
        />
      </div>
    </div>
  );
}
