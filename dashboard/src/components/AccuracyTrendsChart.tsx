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
  data: PerformanceTrend[];
}

export function AccuracyTrendsChart({ data }: Props) {
  if (data.length === 0) {
    return <div className="loading">No performance data available yet.</div>;
  }

  const chartData = data.map((d) => ({
    date: new Date(d.period_start).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    Precision: d.precision_rate ? +(d.precision_rate * 100).toFixed(1) : null,
    Recall: d.recall_rate ? +(d.recall_rate * 100).toFixed(1) : null,
    "F1 Score": d.f1_score ? +(d.f1_score * 100).toFixed(1) : null,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
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
          dataKey="Precision"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={{ r: 4 }}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="Recall"
          stroke="#16a34a"
          strokeWidth={2}
          dot={{ r: 4 }}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="F1 Score"
          stroke="#d97706"
          strokeWidth={2}
          dot={{ r: 4 }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
