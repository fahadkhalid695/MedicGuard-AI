import type { Vitals } from "../types";

interface Props {
  vitals: Vitals | null;
}

interface VitalCardProps {
  label: string;
  value: string;
  unit: string;
  icon: string;
  status: "normal" | "warning" | "critical";
}

function VitalCard({ label, value, unit, icon, status }: VitalCardProps) {
  const statusStyles = {
    normal: "border-green-200",
    warning: "border-yellow-300",
    critical: "border-red-300 bg-red-50",
  };

  return (
    <div className={`vital-card border-l-4 ${statusStyles[status]}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          {label}
        </span>
        <span className="text-lg">{icon}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-bold text-gray-900">{value}</span>
        <span className="text-sm text-gray-500">{unit}</span>
      </div>
    </div>
  );
}

function getHRStatus(hr: number): "normal" | "warning" | "critical" {
  if (hr > 150 || hr < 40) return "critical";
  if (hr > 100 || hr < 50) return "warning";
  return "normal";
}

function getSpo2Status(spo2: number): "normal" | "warning" | "critical" {
  if (spo2 < 88) return "critical";
  if (spo2 < 92) return "warning";
  return "normal";
}

function getBPStatus(sys: number): "normal" | "warning" | "critical" {
  if (sys > 180 || sys < 80) return "critical";
  if (sys > 140 || sys < 90) return "warning";
  return "normal";
}

function getTempStatus(temp: number): "normal" | "warning" | "critical" {
  if (temp > 39.5 || temp < 33) return "critical";
  if (temp > 38.5 || temp < 35) return "warning";
  return "normal";
}

function getRRStatus(rr: number): "normal" | "warning" | "critical" {
  if (rr > 30 || rr < 6) return "critical";
  if (rr > 25 || rr < 8) return "warning";
  return "normal";
}

export function VitalsCards({ vitals }: Props) {
  if (!vitals) {
    return (
      <div className="grid grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="vital-card animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-16 mb-2" />
            <div className="h-8 bg-gray-200 rounded w-12" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-5 gap-3">
      <VitalCard
        label="Heart Rate"
        value={String(vitals.heartRate)}
        unit="bpm"
        icon="♥"
        status={getHRStatus(vitals.heartRate)}
      />
      <VitalCard
        label="Blood Pressure"
        value={`${vitals.bpSystolic}/${vitals.bpDiastolic}`}
        unit="mmHg"
        icon="🩸"
        status={getBPStatus(vitals.bpSystolic)}
      />
      <VitalCard
        label="SpO₂"
        value={String(vitals.spo2)}
        unit="%"
        icon="🫁"
        status={getSpo2Status(vitals.spo2)}
      />
      <VitalCard
        label="Temperature"
        value={vitals.temperature.toFixed(1)}
        unit="°C"
        icon="🌡"
        status={getTempStatus(vitals.temperature)}
      />
      <VitalCard
        label="Resp. Rate"
        value={String(vitals.respiratoryRate)}
        unit="/min"
        icon="💨"
        status={getRRStatus(vitals.respiratoryRate)}
      />
    </div>
  );
}
