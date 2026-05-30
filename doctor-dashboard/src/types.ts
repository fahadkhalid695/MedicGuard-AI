export type Severity = "normal" | "low" | "medium" | "high" | "critical";

export interface Patient {
  id: string;
  name: string;
  severity: Severity;
  heartRate: number;
  spo2: number;
  lastUpdate: string;
}

export interface Vitals {
  heartRate: number;
  bpSystolic: number;
  bpDiastolic: number;
  spo2: number;
  temperature: number;
  respiratoryRate: number;
  timestamp: string;
}

export interface VitalsHistory {
  timestamp: string;
  heartRate: number;
  bpSystolic: number;
  bpDiastolic: number;
  spo2: number;
  temperature: number;
  respiratoryRate: number;
}

export interface AIInsight {
  summary: string;
  action: string;
  severity: Severity;
  confidence: number;
  agents: string[];
  timestamp: string;
}

export interface AlertEvent {
  id: string;
  severity: Severity;
  title: string;
  summary: string;
  timestamp: string;
  status: "active" | "acknowledged" | "resolved";
}

export interface WSMessage {
  type: "vitals_update" | "alert" | "insight" | "patient_list";
  payload: unknown;
}

export interface Consultation {
  id: string;
  patientId: string;
  alertId: string;
  doctorId: string;
  scheduledAt: string;
  telehealthLink: string;
  notes?: string;
  createdAt: string;
}

export interface PatientNote {
  id: string;
  patientId: string;
  doctorId: string;
  content: string;
  createdAt: string;
}

export interface DoctorOverride {
  alertId: string;
  doctorId: string;
  overrideNote: string;
  timestamp: string;
}
