import type { Patient } from "../types";
import { severityColor, severityDot } from "../utils";

interface Props {
  patients: Patient[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function PatientList({ patients, selectedId, onSelect }: Props) {
  // Sort: critical first, then high, medium, etc.
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, normal: 4 };
  const sorted = [...patients].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
  );

  return (
    <aside className="w-80 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
          Patients
        </h2>
        <p className="text-xs text-gray-400 mt-0.5">
          {patients.length} monitored
        </p>
      </div>

      {/* Patient cards */}
      <div className="flex-1 overflow-y-auto">
        {sorted.map((patient) => (
          <button
            key={patient.id}
            onClick={() => onSelect(patient.id)}
            className={`w-full text-left p-4 border-b border-gray-50 transition-colors hover:bg-gray-50 ${
              selectedId === patient.id ? "bg-clinical-50 border-l-4 border-l-clinical-500" : ""
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 text-sm truncate">
                  {patient.name}
                </p>
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="text-xs text-gray-500">
                    ♥ {patient.heartRate} bpm
                  </span>
                  <span className="text-xs text-gray-500">
                    SpO₂ {patient.spo2}%
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${severityDot(patient.severity)}`} />
                <span className={`severity-badge ${severityColor(patient.severity)}`}>
                  {patient.severity === "normal" ? "OK" : patient.severity.toUpperCase()}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}
