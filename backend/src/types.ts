export type AlertOutcome =
  | "true_positive"
  | "false_positive"
  | "true_negative"
  | "false_negative"
  | "doctor_override"
  | "patient_worsened"
  | "resolved_naturally";

export type AlertSeverity = "low" | "medium" | "high" | "critical";
export type ABGroup = "A" | "B";

export interface OutcomeRecord {
  id: string;
  alert_id: string;
  patient_id: string;
  outcome: AlertOutcome;
  agent_id: string;
  condition_type?: string;
  notes?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  vitals_at_alert?: Record<string, number>;
  vitals_at_review?: Record<string, number>;
  time_to_review_min?: number;
}

export interface AgentPerformance {
  id: string;
  agent_id: string;
  condition_type: string | null;
  period_start: string;
  period_end: string;
  total_alerts: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  doctor_overrides: number;
  precision_rate: number | null;
  recall_rate: number | null;
  false_positive_rate: number | null;
  f1_score: number | null;
  ab_group: ABGroup | null;
  threshold_version: string | null;
}

export interface ThresholdConfig {
  id: string;
  version: string;
  agent_id: string;
  thresholds: VitalThresholds;
  source: "manual" | "claude_suggested" | "ab_winner";
  is_active: boolean;
  ab_group: ABGroup | null;
}

export interface VitalThresholds {
  heart_rate: { low: number; high: number; critical_low: number; critical_high: number };
  systolic_bp: { low: number; high: number; critical_low: number; critical_high: number };
  diastolic_bp: { low: number; high: number; critical_low: number; critical_high: number };
  spo2: { low: number; critical_low: number };
  temperature: { low: number; high: number; critical_low: number; critical_high: number };
  respiratory_rate: { low: number; high: number; critical_low: number; critical_high: number };
}

export interface ABTest {
  id: string;
  name: string;
  description?: string;
  agent_id: string;
  status: "draft" | "running" | "completed" | "cancelled";
  config_a_id: string;
  config_b_id: string;
  start_date?: string;
  end_date?: string;
}

export interface TuningSuggestion {
  id: string;
  agent_id: string;
  performance_data: Record<string, unknown>;
  suggestion: Record<string, unknown>;
  applied: boolean;
  applied_as_version?: string;
  created_at: string;
}

export interface PerformanceTrend {
  period_start: string;
  precision_rate: number;
  recall_rate: number;
  f1_score: number;
  false_positive_rate: number;
  total_alerts: number;
}
