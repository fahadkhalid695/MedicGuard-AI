import { useCallback, useRef, useState } from "react";
import { NotificationBar } from "./components/NotificationBar";
import { PatientDetail } from "./components/PatientDetail";
import { PatientList } from "./components/PatientList";
import { useAlertSound } from "./hooks/useAlertSound";
import { useWebSocket } from "./hooks/useWebSocket";
import type {
  AIInsight,
  AlertEvent,
  Patient,
  PatientNote,
  Severity,
  Vitals,
  VitalsHistory,
  WSMessage,
} from "./types";

// Demo doctor ID — in production this comes from auth
const DOCTOR_ID = "dr-001";

// Demo patients — matching the seed data in the database
const INITIAL_PATIENTS: Patient[] = [
  { id: "00000000-0000-0000-0000-000000000001", name: "Sarah Johnson", severity: "normal", heartRate: 72, spo2: 98, lastUpdate: "" },
  { id: "00000000-0000-0000-0000-000000000002", name: "Michael Chen", severity: "normal", heartRate: 68, spo2: 97, lastUpdate: "" },
  { id: "00000000-0000-0000-0000-000000000003", name: "Emily Rodriguez", severity: "normal", heartRate: 75, spo2: 99, lastUpdate: "" },
  { id: "00000000-0000-0000-0000-000000000004", name: "James Williams", severity: "normal", heartRate: 80, spo2: 96, lastUpdate: "" },
  { id: "00000000-0000-0000-0000-000000000005", name: "Maria Garcia", severity: "normal", heartRate: 70, spo2: 98, lastUpdate: "" },
];

const MAX_HISTORY = 90; // ~30 min at 1 reading per 20s

export default function App() {
  const [patients, setPatients] = useState<Patient[]>(INITIAL_PATIENTS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [vitals, setVitals] = useState<Record<string, Vitals>>({});
  const [history, setHistory] = useState<Record<string, VitalsHistory[]>>({});
  const [insights, setInsights] = useState<Record<string, AIInsight>>({});
  const [alerts, setAlerts] = useState<Record<string, AlertEvent[]>>({});
  const [criticalAlert, setCriticalAlert] = useState<AlertEvent | null>(null);
  const [notes, setNotes] = useState<Record<string, PatientNote[]>>({});

  const { playAlertSound } = useAlertSound();
  const patientsRef = useRef(patients);
  patientsRef.current = patients;

  const handleMessage = useCallback(
    (msg: WSMessage) => {
      switch (msg.type) {
        case "vitals_update": {
          const payload = msg.payload as {
            patient_id: string;
            heart_rate: number;
            bp_systolic: number;
            bp_diastolic: number;
            spo2: number;
            temperature: number;
            respiratory_rate: number;
            timestamp: string;
          };

          const newVitals: Vitals = {
            heartRate: payload.heart_rate,
            bpSystolic: payload.bp_systolic,
            bpDiastolic: payload.bp_diastolic,
            spo2: payload.spo2,
            temperature: payload.temperature,
            respiratoryRate: payload.respiratory_rate,
            timestamp: payload.timestamp,
          };

          // Update current vitals
          setVitals((prev) => ({ ...prev, [payload.patient_id]: newVitals }));

          // Append to history
          setHistory((prev) => {
            const existing = prev[payload.patient_id] || [];
            const updated = [...existing, { ...newVitals, timestamp: payload.timestamp }];
            return {
              ...prev,
              [payload.patient_id]: updated.slice(-MAX_HISTORY),
            };
          });

          // Update patient list card
          setPatients((prev) =>
            prev.map((p) =>
              p.id === payload.patient_id
                ? { ...p, heartRate: payload.heart_rate, spo2: payload.spo2, lastUpdate: payload.timestamp }
                : p
            )
          );
          break;
        }

        case "alert": {
          const payload = msg.payload as {
            patient_id: string;
            severity: Severity;
            summary: string;
            action: string;
            confidence: number;
            dashboard_link: string;
            timestamp: string;
          };

          const alertEvent: AlertEvent = {
            id: `alert-${Date.now()}`,
            severity: payload.severity,
            title: payload.action,
            summary: payload.summary,
            timestamp: payload.timestamp,
            status: "active",
          };

          // Add to alert history
          setAlerts((prev) => {
            const existing = prev[payload.patient_id] || [];
            return {
              ...prev,
              [payload.patient_id]: [alertEvent, ...existing].slice(0, 50),
            };
          });

          // Update patient severity
          setPatients((prev) =>
            prev.map((p) =>
              p.id === payload.patient_id ? { ...p, severity: payload.severity } : p
            )
          );

          // Critical alert: show notification bar + sound
          if (payload.severity === "critical") {
            setCriticalAlert(alertEvent);
            playAlertSound();
          }
          break;
        }

        case "insight": {
          const payload = msg.payload as {
            patient_id: string;
            summary: string;
            action: string;
            severity: Severity;
            confidence: number;
            agents: string[];
            timestamp: string;
          };

          setInsights((prev) => ({
            ...prev,
            [payload.patient_id]: {
              summary: payload.summary,
              action: payload.action,
              severity: payload.severity,
              confidence: payload.confidence,
              agents: payload.agents,
              timestamp: payload.timestamp,
            },
          }));
          break;
        }

        case "patient_list": {
          const payload = msg.payload as Patient[];
          setPatients(payload);
          break;
        }
      }
    },
    [playAlertSound]
  );

  const patientIds = patients.map((p) => p.id);
  const { connected } = useWebSocket({
    doctorId: DOCTOR_ID,
    patientIds,
    onMessage: handleMessage,
  });

  const selectedPatient = patients.find((p) => p.id === selectedId) || null;

  // Handlers for doctor actions
  const handleAlertAcknowledged = useCallback((alertId: string) => {
    setAlerts((prev) => {
      const updated = { ...prev };
      for (const pid of Object.keys(updated)) {
        updated[pid] = updated[pid].map((a) =>
          a.id === alertId ? { ...a, status: "acknowledged" as const } : a
        );
      }
      return updated;
    });
  }, []);

  const handleNoteAdded = useCallback((note: PatientNote) => {
    setNotes((prev) => ({
      ...prev,
      [note.patientId]: [note, ...(prev[note.patientId] || [])],
    }));
  }, []);

  const handleEscalated = useCallback((patientId: string) => {
    setPatients((prev) =>
      prev.map((p) => (p.id === patientId ? { ...p, severity: "critical" as Severity } : p))
    );
  }, []);

  return (
    <div className="h-screen flex flex-col">
      {/* Critical alert notification bar */}
      <NotificationBar alert={criticalAlert} onDismiss={() => setCriticalAlert(null)} />

      {/* Top header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-gray-900">MediGuard AI</h1>
          <span className="text-xs bg-clinical-100 text-clinical-700 px-2 py-0.5 rounded-full font-medium">
            Doctor Dashboard
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`}
            />
            <span className="text-xs text-gray-500">
              {connected ? "Connected" : "Reconnecting..."}
            </span>
          </div>
          <span className="text-sm text-gray-600">Dr. Smith</span>
        </div>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar: patient list */}
        <PatientList
          patients={patients}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />

        {/* Main content: patient detail */}
        <PatientDetail
          patient={selectedPatient}
          vitals={selectedId ? vitals[selectedId] || null : null}
          history={selectedId ? history[selectedId] || [] : []}
          insight={selectedId ? insights[selectedId] || null : null}
          alerts={selectedId ? alerts[selectedId] || [] : []}
          doctorId={DOCTOR_ID}
          notes={selectedId ? notes[selectedId] || [] : []}
          onAlertAcknowledged={handleAlertAcknowledged}
          onNoteAdded={handleNoteAdded}
          onEscalated={handleEscalated}
        />
      </div>
    </div>
  );
}
