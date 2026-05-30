import type { AIInsight, AlertEvent, Patient, PatientNote, Vitals, VitalsHistory } from "../types";
import { AIInsightPanel } from "./AIInsightPanel";
import { AlertTimeline } from "./AlertTimeline";
import { DoctorActionPanel } from "./DoctorActionPanel";
import { VitalsCards } from "./VitalsCards";
import { VitalsChart } from "./VitalsChart";

interface Props {
  patient: Patient | null;
  vitals: Vitals | null;
  history: VitalsHistory[];
  insight: AIInsight | null;
  alerts: AlertEvent[];
  doctorId: string;
  notes: PatientNote[];
  onAlertAcknowledged: (alertId: string) => void;
  onNoteAdded: (note: PatientNote) => void;
  onEscalated: (patientId: string) => void;
}

export function PatientDetail({
  patient,
  vitals,
  history,
  insight,
  alerts,
  doctorId,
  notes,
  onAlertAcknowledged,
  onNoteAdded,
  onEscalated,
}: Props) {
  if (!patient) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-4xl mb-3">👈</p>
          <p className="text-gray-500 text-sm">Select a patient to view their live vitals</p>
        </div>
      </div>
    );
  }

  // Find the most recent active alert
  const activeAlert = alerts.find((a) => a.status === "active") || null;

  return (
    <main className="flex-1 overflow-y-auto p-6 space-y-4">
      {/* Patient header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{patient.name}</h1>
          <p className="text-sm text-gray-500">
            Patient ID: {patient.id.slice(0, 8)}... • Last update:{" "}
            {patient.lastUpdate ? new Date(patient.lastUpdate).toLocaleTimeString() : "—"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-gray-500">Live</span>
        </div>
      </div>

      {/* Live vitals cards */}
      <VitalsCards vitals={vitals} />

      {/* Doctor Action Panel (visible when alert is active) */}
      {(activeAlert || notes.length > 0) && (
        <DoctorActionPanel
          patientId={patient.id}
          patientName={patient.name}
          doctorId={doctorId}
          activeAlert={activeAlert}
          notes={notes}
          onAlertAcknowledged={onAlertAcknowledged}
          onNoteAdded={onNoteAdded}
          onEscalated={() => onEscalated(patient.id)}
        />
      )}

      {/* Vitals trend chart */}
      <VitalsChart history={history} />

      {/* AI Insight + Alert Timeline side by side */}
      <div className="grid grid-cols-2 gap-4">
        <AIInsightPanel insight={insight} />
        <AlertTimeline alerts={alerts} />
      </div>
    </main>
  );
}
