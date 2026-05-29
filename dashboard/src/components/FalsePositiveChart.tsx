import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { PerformanceTrend } from "../api";

interface Props {
  data: PerformanceTrend[];
}

export function FalsePositiveChart({ data }: Props) {
  if (data.length === 0) {
    return <div className="loading">No performance data available yet.</div>;
  }

  const chartData = data.map((d) => ({
    date: new Date(d.period_start).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    "FP Rate": d.false_positive_rate ? +(d.false_positive_rate * 100).toFixed(1) : null,
    Alerts: d.total_alerts,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="date" fontSize={12} tick={{ fill: "#64748b" }} />
        <YAxis
          domain={[0, 50]}
          fontSize={12}
          tick={{ fill: "#64748b" }}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          formatter={(value: number, name: string) =>
            name === "FP Rate" ? `${value}%` : value
          }
          contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0" }}
        />
        {/* Target line: keep FP rate below 15% */}
        <ReferenceLine
          y={15}
          stroke="#dc2626"
          strokeDasharray="5 5"
          label={{ value: "Target: <15%", position: "right", fill: "#dc2626", fontSize: 11 }}
        />
        <Line
          type="monotone"
          dataKey="FP Rate"
          stroke="#dc2626"
          strokeWidth={2}
          dot={{ r: 4, fill: "#dc2626" }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
