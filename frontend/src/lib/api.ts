import type {
  HealthResponse,
  SignalsResponse,
  SignalEnvelope,
  SignalStats,
  ModelsResponse,
  GenerateSignalRequest,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/v1/health");
  },

  signals(page = 1, perPage = 20): Promise<SignalsResponse> {
    return request<SignalsResponse>(
      `/api/v1/signals?page=${page}&per_page=${perPage}`
    );
  },

  generateSignal(data: GenerateSignalRequest): Promise<SignalEnvelope> {
    return request<SignalEnvelope>("/api/v1/signal", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  stats(): Promise<SignalStats> {
    return request<SignalStats>("/api/v1/stats");
  },

  models(): Promise<ModelsResponse> {
    return request<ModelsResponse>("/api/v1/models");
  },
};
