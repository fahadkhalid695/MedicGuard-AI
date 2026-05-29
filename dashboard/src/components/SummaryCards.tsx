import type { PerformanceSummary } from "../api";

interface Props {
  summary: PerformanceSummary;
}

function rateClass(value: number | null, goodThreshold: number, badThreshold: number): string {
  if (value === null) return "neutral";
  if (value >= goodThreshold) return "good";
  if (value < badThreshold) return "bad";
  return "warning";
}

function formatRate(value: number | null): string {
  if (value === null) return "N/A";
  return `${(value * 100).toFixed(1)}%`;
}

export function SummaryCards({ summary }: Props) {
  return (
    <div className="summary-cards">
      <div className="summary-card">
        <div className="label">Precision</div>
        <div className={`value ${rateClass(summary.precision_rate, 0.85, 0.7)}`}>
          {formatRate(summary.precision_rate)}
        </div>
      </div>

      <div className="summary-card">
        <div className="label">Recall</div>
        <div className={`value ${rateClass(summary.recall_rate, 0.9, 0.8)}`}>
          {formatRate(summary.recall_rate)}
        </div>
      </div>

      <div className="summary-card">
        <div className="label">F1 Score</div>
        <div className={`value ${rateClass(summary.f1_score, 0.85, 0.7)}`}>
          {formatRate(summary.f1_score)}
        </div>
      </div>

      <div className="summary-card">
        <div className="label">False Positive Rate</div>
        <div className={`value ${summary.false_positive_rate && summary.false_positive_rate > 0.2 ? "bad" : summary.false_positive_rate && summary.false_positive_rate > 0.1 ? "warning" : "good"}`}>
          {formatRate(summary.false_positive_rate)}
        </div>
      </div>

      <div className="summary-card">
        <div className="label">Total Alerts</div>
        <div className="value neutral">{summary.total_alerts}</div>
      </div>

      <div className="summary-card">
        <div className="label">Doctor Overrides</div>
        <div className={`value ${summary.doctor_overrides > summary.total_alerts * 0.2 ? "bad" : "neutral"}`}>
          {summary.doctor_overrides}
        </div>
      </div>
    </div>
  );
}
