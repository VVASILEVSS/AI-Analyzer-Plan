"use client";

import { useState } from "react";
import { Settings, Globe, Save, ArrowLeft, Info } from "lucide-react";
import Link from "next/link";

const PAIRS = [
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
  "MATIC/USDT",
  "XAU/USDT",
];

interface AppSettings {
  backendUrl: string;
  defaultPair: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("ai-analyzer-settings");
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {
          // ignore
        }
      }
    }
    return {
      backendUrl: "http://localhost:8000",
      defaultPair: "BTC/USDT",
    };
  });

  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    localStorage.setItem("ai-analyzer-settings", JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-dark-muted">
        <Link href="/" className="flex items-center gap-1 hover:text-dark-text transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Dashboard
        </Link>
        <span>/</span>
        <span className="text-dark-text">Settings</span>
      </div>

      {/* Page header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-dark-card border border-dark-border">
          <Settings className="w-5 h-5 text-dark-muted" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-dark-text">Settings</h1>
          <p className="text-sm text-dark-muted">
            Configure your AI Analyzer preferences
          </p>
        </div>
      </div>

      {/* Settings form */}
      <div className="space-y-4">
        {/* Backend URL */}
        <div className="rounded-xl border border-dark-border bg-dark-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-dark-muted" />
            <label className="text-sm font-medium text-dark-text">
              Backend API URL
            </label>
          </div>
          <input
            type="text"
            value={settings.backendUrl}
            onChange={(e) =>
              setSettings((s) => ({ ...s, backendUrl: e.target.value }))
            }
            className="w-full px-3 py-2.5 rounded-lg bg-dark-bg border border-dark-border text-dark-text text-sm focus:outline-none focus:border-accent-green/50 focus:ring-1 focus:ring-accent-green/20 transition-colors placeholder:text-dark-muted"
            placeholder="http://localhost:8000"
          />
          <p className="text-xs text-dark-muted flex items-start gap-1.5">
            <Info className="w-3 h-3 mt-0.5 shrink-0" />
            The URL of the FastAPI backend server. Requires a page reload to take effect.
          </p>
        </div>

        {/* Default pair */}
        <div className="rounded-xl border border-dark-border bg-dark-card p-5 space-y-3">
          <label className="text-sm font-medium text-dark-text">
            Default Trading Pair
          </label>
          <select
            value={settings.defaultPair}
            onChange={(e) =>
              setSettings((s) => ({ ...s, defaultPair: e.target.value }))
            }
            className="w-full px-3 py-2.5 rounded-lg bg-dark-bg border border-dark-border text-dark-text text-sm focus:outline-none focus:border-accent-green/50 focus:ring-1 focus:ring-accent-green/20 transition-colors appearance-none cursor-pointer"
          >
            {PAIRS.map((pair) => (
              <option key={pair} value={pair}>
                {pair}
              </option>
            ))}
          </select>
          <p className="text-xs text-dark-muted flex items-start gap-1.5">
            <Info className="w-3 h-3 mt-0.5 shrink-0" />
            The pair that will be pre-selected when opening the dashboard.
          </p>
        </div>

        {/* Save button */}
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-accent-green hover:bg-accent-green/90 text-dark-bg font-medium text-sm transition-colors"
        >
          <Save className="w-4 h-4" />
          {saved ? "Saved!" : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
