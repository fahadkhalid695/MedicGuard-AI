const API_BASE = "/api/feedback";

export interface PerformanceTrend {
  period_start: string;
  precision_rate: number | null;
  recall_rate: number | null;
  f1_score: number | null;
  false_positive_rate: number | null;
  total_alerts: number;
  ab_group: string | null;
  threshold_version: string | null;
}

export interface PerformanceSummary {
  agent_id: string;
  period_start: string;
  period_end: string;
  precision_rate: number | null;
  recall_rate: number | null;
  f1_score: number | null;
  false_positive_rate: number | null;
  total_alerts: number;
  true_positives: number;
  false_positives: number;
  doctor_overrides: number;
  threshold_version: string | null;
}

export interface TuningSuggestion {
  id: string;
  agent_id: string;
  suggestion: {
    suggested_thresholds: Record<string, unknown>;
    reasoning: string;
  };
  applied: boolean;
  created_at: string;
}

export async function fetchPerformanceTrends(
  agentId: string,
  weeks = 12
): Promise<PerformanceTrend[]> {
  const res = await fetch(`${API_BASE}/performance/${agentId}/trends?weeks=${weeks}`);
  if (!res.ok) throw new Error("Failed to fetch trends");
  return res.json();
}

export async function fetchPerformanceSummary(): Promise<PerformanceSummary[]> {
  const res = await fetch(`${API_BASE}/performance/summary`);
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

export async function fetchTuningSuggestions(agentId?: string): Promise<TuningSuggestion[]> {
  const url = agentId
    ? `${API_BASE}/tuning-suggestions?agent_id=${agentId}`
    : `${API_BASE}/tuning-suggestions`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch suggestions");
  return res.json();
}

export async function activateThreshold(configId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/thresholds/${configId}/activate`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to activate threshold");
}
