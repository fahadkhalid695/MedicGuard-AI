import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PerformanceTrend } from "../api";

interface Props {
  agentId: string;
  trends: PerformanceTrend[];
}

export function ABComparisonPanel({ agentId: _agentId, trends }: Props) {
  const groupA = trends.filter((t) => t.ab_group === "A");
  const groupB = trends.filter((t) => t.ab_group === "B");

  if (groupA.length === 0 && groupB.length === 0) {
    return (
      <div className="loading">
        No active A/B test data. Create an A/B test to compare threshold configurations.
      </div>
    );
  }

  // Merge A and B data by date for the chart
  const dateMap = new Map<string, { date: string; precisionA?: number; precisionB?: number; f1A?: number; f1B?: number }>();

  for (const t of groupA) {
    const date = new Date(t.period_start).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const entry = dateMap.get(date) || { date };
    entry.precisionA = t.precision_rate ? +(t.precision_rate * 100).toFixed(1) : undefined;
    entry.f1A = t.f1_score ? +(t.f1_score * 100).toFixed(1) : undefined;
    dateMap.set(date, entry);
  }

  for (const t of groupB) {
    const date = new Date(t.period_start).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const entry = dateMap.get(date) || { date };
    entry.precisionB = t.precision_rate ? +(t.precision_rate * 100).toFixed(1) : undefined;
    entry.f1B = t.f1_score ? +(t.f1_score * 100).toFixed(1) : undefined;
    dateMap.set(date, entry);
  }

  const chartData = Array.from(dateMap.values());

  // Summary stats
  const avgPrecisionA = groupA.length > 0
    ? groupA.reduce((sum, t) => sum + (t.precision_rate || 0), 0) / groupA.length
    : null;
  const avgPrecisionB = groupB.length > 0
    ? groupB.reduce((sum, t) => sum + (t.precision_rate || 0), 0) / groupB.length
    : null;
  const avgFprA = groupA.length > 0
    ? groupA.reduce((sum, t) => sum + (t.false_positive_rate || 0), 0) / groupA.length
    : null;
  const avgFprB = groupB.length > 0
    ? groupB.reduce((sum, t) => sum + (t.false_positive_rate || 0), 0) / groupB.length
    : null;

  return (
    <div>
      {/* A/B summary boxes */}
      <div className="ab-comparison">
        <div className="ab-group group-a">
          <h3>Group A (Control)</h3>
          <div className="metric">
            <span>Avg Precision</span>
            <span>{avgPrecisionA ? `${(avgPrecisionA * 100).toFixed(1)}%` : "N/A"}</span>
          </div>
          <div className="metric">
            <span>Avg FP Rate</span>
            <span>{avgFprA ? `${(avgFprA * 100).toFixed(1)}%` : "N/A"}</span>
          </div>
          <div className="metric">
            <span>Data Points</span>
            <span>{groupA.length}</span>
          </div>
          <div className="metric">
            <span>Threshold</span>
            <span>{groupA[0]?.threshold_version || "—"}</span>
          </div>
        </div>

        <div className="ab-group group-b">
          <h3>Group B (Experiment)</h3>
          <div className="metric">
            <span>Avg Precision</span>
            <span>{avgPrecisionB ? `${(avgPrecisionB * 100).toFixed(1)}%` : "N/A"}</span>
          </div>
          <div className="metric">
            <span>Avg FP Rate</span>
            <span>{avgFprB ? `${(avgFprB * 100).toFixed(1)}%` : "N/A"}</span>
          </div>
          <div className="metric">
            <span>Data Points</span>
            <span>{groupB.length}</span>
          </div>
          <div className="metric">
            <span>Threshold</span>
            <span>{groupB[0]?.threshold_version || "—"}</span>
          </div>
        </div>
      </div>

      {/* A/B comparison chart */}
      {chartData.length > 0 && (
        <div style={{ marginTop: "1.5rem" }}>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" fontSize={12} tick={{ fill: "#64748b" }} />
              <YAxis
                domain={[0, 100]}
                fontSize={12}
                tick={{ fill: "#64748b" }}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                formatter={(value: number) => `${value}%`}
                contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0" }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="precisionA"
                name="Precision (A)"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="precisionB"
                name="Precision (B)"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="f1A"
                name="F1 (A)"
                stroke="#3b82f6"
                strokeWidth={1}
                strokeDasharray="5 5"
                dot={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="f1B"
                name="F1 (B)"
                stroke="#8b5cf6"
                strokeWidth={1}
                strokeDasharray="5 5"
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
