import { useState } from "react";
import {
  acknowledgeAlert,
  addPatientNote,
  createConsultation,
  escalateToHospital,
  overrideRecommendation,
} from "../api";
import type { AlertEvent, PatientNote } from "../types";
import { ConsultModal } from "./ConsultModal";

interface Props {
  patientId: string;
  patientName: string;
  doctorId: string;
  activeAlert: AlertEvent | null;
  notes: PatientNote[];
  onAlertAcknowledged: (alertId: string) => void;
  onNoteAdded: (note: PatientNote) => void;
  onEscalated: () => void;
}

type ActionStatus = "idle" | "loading" | "success" | "error";

export function DoctorActionPanel({
  patientId,
  patientName,
  doctorId,
  activeAlert,
  notes,
  onAlertAcknowledged,
  onNoteAdded,
  onEscalated,
}: Props) {
  // Action states
  const [ackStatus, setAckStatus] = useState<ActionStatus>("idle");
  const [escalateStatus, setEscalateStatus] = useState<ActionStatus>("idle");
  const [overrideText, setOverrideText] = useState("");
  const [overrideStatus, setOverrideStatus] = useState<ActionStatus>("idle");
  const [noteText, setNoteText] = useState("");
  const [noteStatus, setNoteStatus] = useState<ActionStatus>("idle");
  const [showConsultModal, setShowConsultModal] = useState(false);
  const [consultScheduled, setConsultScheduled] = useState(false);

  // No active alert — show minimal panel
  if (!activeAlert || activeAlert.status !== "active") {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <span>🩺</span> Doctor Actions
        </h3>
        <p className="text-sm text-gray-400 mb-4">No active alert. Actions available when an alert is triggered.</p>

        {/* Patient notes always available */}
        <PatientNotesSection
          notes={notes}
          noteText={noteText}
          setNoteText={setNoteText}
          noteStatus={noteStatus}
          onSubmitNote={async () => {
            if (!noteText.trim()) return;
            setNoteStatus("loading");
            const newNote: PatientNote = {
              id: `note-${Date.now()}`,
              patientId,
              doctorId,
              content: noteText.trim(),
              createdAt: new Date().toISOString(),
            };
            onNoteAdded(newNote); // optimistic
            setNoteText("");
            setNoteStatus("success");
            try {
              await addPatientNote({ patientId, doctorId, content: newNote.content });
            } catch {
              setNoteStatus("error");
            }
            setTimeout(() => setNoteStatus("idle"), 2000);
          }}
        />
      </div>
    );
  }

  // Handlers
  const handleAcknowledge = async () => {
    setAckStatus("loading");
    onAlertAcknowledged(activeAlert.id); // optimistic
    try {
      await acknowledgeAlert({ alertId: activeAlert.id, doctorId });
      setAckStatus("success");
    } catch {
      setAckStatus("error");
    }
    setTimeout(() => setAckStatus("idle"), 2000);
  };

  const handleOverride = async () => {
    if (!overrideText.trim()) return;
    setOverrideStatus("loading");
    try {
      await overrideRecommendation({
        alertId: activeAlert.id,
        doctorId,
        overrideNote: overrideText.trim(),
      });
      setOverrideStatus("success");
      setOverrideText("");
    } catch {
      setOverrideStatus("error");
    }
    setTimeout(() => setOverrideStatus("idle"), 2000);
  };

  const handleEscalate = async () => {
    if (!confirm("This will trigger CRITICAL notification flow (SMS, email, hospital). Continue?")) return;
    setEscalateStatus("loading");
    onEscalated(); // optimistic
    try {
      await escalateToHospital({
        alertId: activeAlert.id,
        patientId,
        doctorId,
        reason: `Manual escalation by ${doctorId}: ${activeAlert.summary}`,
      });
      setEscalateStatus("success");
    } catch {
      setEscalateStatus("error");
    }
    setTimeout(() => setEscalateStatus("idle"), 2000);
  };

  const handleConsultSubmit = async (data: {
    scheduledAt: string;
    telehealthLink: string;
    notes: string;
  }) => {
    setConsultScheduled(true);
    try {
      await createConsultation({
        patientId,
        alertId: activeAlert.id,
        doctorId,
        scheduledAt: new Date(data.scheduledAt).toISOString(),
        telehealthLink: data.telehealthLink,
        notes: data.notes,
      });
    } catch {
      setConsultScheduled(false);
    }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    setNoteStatus("loading");
    const newNote: PatientNote = {
      id: `note-${Date.now()}`,
      patientId,
      doctorId,
      content: noteText.trim(),
      createdAt: new Date().toISOString(),
    };
    onNoteAdded(newNote); // optimistic
    setNoteText("");
    setNoteStatus("success");
    try {
      await addPatientNote({ patientId, doctorId, content: newNote.content });
    } catch {
      setNoteStatus("error");
    }
    setTimeout(() => setNoteStatus("idle"), 2000);
  };

  return (
    <>
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <span>🩺</span> Doctor Actions
          <span className="ml-auto text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
            Alert Active
          </span>
        </h3>

        {/* Action buttons row */}
        <div className="grid grid-cols-2 gap-2">
          {/* Acknowledge */}
          <button
            onClick={handleAcknowledge}
            disabled={ackStatus === "loading" || ackStatus === "success"}
            className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              ackStatus === "success"
                ? "bg-green-100 text-green-700 border border-green-200"
                : "bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100"
            } disabled:opacity-60`}
          >
            {ackStatus === "loading" ? (
              <Spinner />
            ) : ackStatus === "success" ? (
              "✓ Acknowledged"
            ) : (
              <>
                <span>👁</span> Acknowledge Alert
              </>
            )}
          </button>

          {/* Schedule Consult */}
          <button
            onClick={() => setShowConsultModal(true)}
            disabled={consultScheduled}
            className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              consultScheduled
                ? "bg-green-100 text-green-700 border border-green-200"
                : "bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100"
            } disabled:opacity-60`}
          >
            {consultScheduled ? "✓ Consult Scheduled" : <><span>📅</span> Schedule Consult</>}
          </button>

          {/* Escalate to Hospital */}
          <button
            onClick={handleEscalate}
            disabled={escalateStatus === "loading" || escalateStatus === "success"}
            className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 col-span-2 ${
              escalateStatus === "success"
                ? "bg-green-100 text-green-700 border border-green-200"
                : "bg-red-50 text-red-700 border border-red-200 hover:bg-red-100"
            } disabled:opacity-60`}
          >
            {escalateStatus === "loading" ? (
              <Spinner />
            ) : escalateStatus === "success" ? (
              "✓ Escalated to Hospital"
            ) : (
              <>
                <span>🏥</span> Escalate to Hospital
              </>
            )}
          </button>
        </div>

        {/* Override AI Recommendation */}
        <div>
          <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1.5">
            Override AI Recommendation
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={overrideText}
              onChange={(e) => setOverrideText(e.target.value)}
              placeholder="Enter your clinical assessment..."
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-clinical-500 focus:border-clinical-500 outline-none"
              onKeyDown={(e) => e.key === "Enter" && handleOverride()}
            />
            <button
              onClick={handleOverride}
              disabled={!overrideText.trim() || overrideStatus === "loading"}
              className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {overrideStatus === "loading" ? <Spinner /> : overrideStatus === "success" ? "✓" : "Save"}
            </button>
          </div>
          {overrideStatus === "success" && (
            <p className="text-xs text-green-600 mt-1">Override saved alongside AI recommendation.</p>
          )}
          {overrideStatus === "error" && (
            <p className="text-xs text-red-600 mt-1">Failed to save. Will retry.</p>
          )}
        </div>

        {/* Divider */}
        <hr className="border-gray-100" />

        {/* Patient Notes */}
        <PatientNotesSection
          notes={notes}
          noteText={noteText}
          setNoteText={setNoteText}
          noteStatus={noteStatus}
          onSubmitNote={handleAddNote}
        />
      </div>

      {/* Consult Modal */}
      <ConsultModal
        isOpen={showConsultModal}
        onClose={() => setShowConsultModal(false)}
        onSubmit={handleConsultSubmit}
        patientName={patientName}
      />
    </>
  );
}

// --- Sub-components ---

function PatientNotesSection({
  notes,
  noteText,
  setNoteText,
  noteStatus,
  onSubmitNote,
}: {
  notes: PatientNote[];
  noteText: string;
  setNoteText: (v: string) => void;
  noteStatus: ActionStatus;
  onSubmitNote: () => void;
}) {
  return (
    <div>
      <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1.5">
        Patient Notes
      </label>

      {/* Note input */}
      <div className="flex gap-2 mb-2">
        <input
          type="text"
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder="Add a quick note..."
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-clinical-500 focus:border-clinical-500 outline-none"
          onKeyDown={(e) => e.key === "Enter" && onSubmitNote()}
        />
        <button
          onClick={onSubmitNote}
          disabled={!noteText.trim() || noteStatus === "loading"}
          className="px-4 py-2 bg-gray-700 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {noteStatus === "loading" ? <Spinner /> : "Add"}
        </button>
      </div>

      {/* Recent notes */}
      {notes.length > 0 && (
        <div className="max-h-32 overflow-y-auto space-y-1.5">
          {notes.slice(0, 5).map((note) => (
            <div key={note.id} className="bg-gray-50 rounded-lg px-3 py-2 text-xs">
              <p className="text-gray-700">{note.content}</p>
              <p className="text-gray-400 mt-0.5">
                {new Date(note.createdAt).toLocaleTimeString()} — {note.doctorId}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
