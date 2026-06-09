export type SignalType = "BUY" | "SELL" | "HOLD";

export interface SignalPipeline {
  elapsed: number;
  ml_filter: Record<string, unknown>;
  regime: Record<string, unknown>;
  llm_elapsed: number;
  from_cache: boolean;
}

export interface SignalEnvelope {
  signal: SignalType;
  confidence: number;
  pair: string;
  timeframe: string;
  regime?: string;
  ml_verdict?: string;
  ml_probability?: number;
  reasons: string[];
  risks: string[];
  model_used: string;
  timestamp: string;
  sha256: string;
  from_cache?: boolean;
  pipeline?: SignalPipeline;
}

export interface HealthResponse {
  status: string;
  ollama: boolean;
  model: string;
  vram_tier: string;
}

export interface SignalsResponse {
  signals: SignalEnvelope[];
  total: number;
  page: number;
  per_page: number;
}

export interface SignalStats {
  total_generated: number;
  by_signal: Record<SignalType, number>;
  by_regime: Record<string, number>;
  avg_confidence: number;
}

export interface ModelsResponse {
  available: string[];
  configured: string;
  default: string;
  vram_tier: string;
}

export interface GenerateSignalRequest {
  pair: string;
  timeframe: string;
  market_data?: Record<string, unknown>;
  force_refresh?: boolean;
}
