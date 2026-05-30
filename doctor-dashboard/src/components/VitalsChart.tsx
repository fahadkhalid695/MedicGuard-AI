import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { VitalsHistory } from "../types";
import { formatTime } from "../utils";

interface Props {
  history: VitalsHistory[];
}

export function VitalsChart({ history }: Props) {
  if (history.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center justify-center h-72">
        <p className="text-gray-400 text-sm">Waiting for vitals data...</p>
      </div>
    );
  }

  const chartData = history.map((h) => ({
    time: formatTime(h.timestamp),
    "Heart Rate": h.heartRate,
    SpO2: h.spo2,
    "Systolic BP": h.bpSystolic,
    Temperature: h.temperature,
    "Resp Rate": h.respiratoryRate,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Vitals Trend — Last 30 Minutes
      </h3>

      <div className="grid grid-cols-2 gap-4">
        {/* Heart Rate + SpO2 */}
        <div>
          <p className="text-xs text-gray-500 mb-1 font-medium">Heart Rate & SpO₂</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" fontSize={10} tick={{ fill: "#94a3b8" }} interval="preserveStartEnd" />
              <YAxis yAxisId="hr" domain={[40, 180]} fontSize={10} tick={{ fill: "#94a3b8" }} />
              <YAxis yAxisId="spo2" orientation="right" domain={[80, 100]} fontSize={10} tick={{ fill: "#94a3b8" }} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <ReferenceLine yAxisId="hr" y={100} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.5} />
              <Line yAxisId="hr" type="monotone" dataKey="Heart Rate" stroke="#ef4444" strokeWidth={2} dot={false} />
              <Line yAxisId="spo2" type="monotone" dataKey="SpO2" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Blood Pressure */}
        <div>
          <p className="text-xs text-gray-500 mb-1 font-medium">Systolic Blood Pressure</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" fontSize={10} tick={{ fill: "#94a3b8" }} interval="preserveStartEnd" />
              <YAxis domain={[70, 200]} fontSize={10} tick={{ fill: "#94a3b8" }} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <ReferenceLine y={140} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.5} />
              <ReferenceLine y={180} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />
              <Line type="monotone" dataKey="Systolic BP" stroke="#8b5cf6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Temperature */}
        <div>
          <p className="text-xs text-gray-500 mb-1 font-medium">Temperature</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" fontSize={10} tick={{ fill: "#94a3b8" }} interval="preserveStartEnd" />
              <YAxis domain={[35, 40]} fontSize={10} tick={{ fill: "#94a3b8" }} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <ReferenceLine y={38.5} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.5} />
              <Line type="monotone" dataKey="Temperature" stroke="#f97316" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Respiratory Rate */}
        <div>
          <p className="text-xs text-gray-500 mb-1 font-medium">Respiratory Rate</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" fontSize={10} tick={{ fill: "#94a3b8" }} interval="preserveStartEnd" />
              <YAxis domain={[5, 35]} fontSize={10} tick={{ fill: "#94a3b8" }} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <ReferenceLine y={25} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.5} />
              <Line type="monotone" dataKey="Resp Rate" stroke="#06b6d4" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
