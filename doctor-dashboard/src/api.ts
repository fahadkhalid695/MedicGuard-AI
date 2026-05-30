/**
 * REST API client for doctor actions.
 * All calls are fire-and-forget with optimistic UI updates.
 */

const API_BASE = "/api";

export interface AcknowledgeAlertPayload {
  alertId: string;
  doctorId: string;
}

export interface OverridePayload {
  alertId: string;
  doctorId: string;
  overrideNote: string;
}

export interface EscalatePayload {
  alertId: string;
  patientId: string;
  doctorId: string;
  reason: string;
}

export interface CreateConsultationPayload {
  patientId: string;
  alertId: string;
  doctorId: string;
  scheduledAt: string;
  telehealthLink: string;
  notes?: string;
}

export interface AddNotePayload {
  patientId: string;
  doctorId: string;
  content: string;
}

export async function acknowledgeAlert(payload: AcknowledgeAlertPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/alerts/${payload.alertId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status: "acknowledged",
      acknowledged_by: payload.doctorId,
      acknowledged_at: new Date().toISOString(),
    }),
  });
  if (!res.ok) throw new Error(`Failed to acknowledge alert: ${res.status}`);
}

export async function overrideRecommendation(payload: OverridePayload): Promise<void> {
  const res = await fetch(`${API_BASE}/alerts/${payload.alertId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      doctor_override: payload.overrideNote,
      override_by: payload.doctorId,
      override_at: new Date().toISOString(),
    }),
  });
  if (!res.ok) throw new Error(`Failed to save override: ${res.status}`);
}

export async function escalateToHospital(payload: EscalatePayload): Promise<void> {
  const res = await fetch(`${API_BASE}/alerts/${payload.alertId}/escalate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_id: payload.patientId,
      doctor_id: payload.doctorId,
      reason: payload.reason,
      escalated_at: new Date().toISOString(),
    }),
  });
  if (!res.ok) throw new Error(`Failed to escalate: ${res.status}`);
}

export async function createConsultation(payload: CreateConsultationPayload): Promise<{ id: string }> {
  const res = await fetch(`${API_BASE}/consultations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_id: payload.patientId,
      alert_id: payload.alertId,
      doctor_id: payload.doctorId,
      scheduled_at: payload.scheduledAt,
      telehealth_link: payload.telehealthLink,
      notes: payload.notes || "",
    }),
  });
  if (!res.ok) throw new Error(`Failed to create consultation: ${res.status}`);
  return res.json();
}

export async function addPatientNote(payload: AddNotePayload): Promise<{ id: string }> {
  const res = await fetch(`${API_BASE}/patients/${payload.patientId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      doctor_id: payload.doctorId,
      content: payload.content,
      created_at: new Date().toISOString(),
    }),
  });
  if (!res.ok) throw new Error(`Failed to add note: ${res.status}`);
  return res.json();
}
