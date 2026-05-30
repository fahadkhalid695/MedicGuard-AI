-- MediGuard AI - Consultations & Patient Notes
-- ==============================================

-- Consultations scheduled by doctors in response to alerts
CREATE TABLE consultations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    alert_id        UUID REFERENCES alerts(id) ON DELETE SET NULL,
    doctor_id       UUID NOT NULL REFERENCES care_team_members(id),
    scheduled_at    TIMESTAMPTZ NOT NULL,
    telehealth_link VARCHAR(500),
    notes           TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled',  -- scheduled, completed, cancelled
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_consultations_patient ON consultations (patient_id, scheduled_at DESC);
CREATE INDEX idx_consultations_doctor ON consultations (doctor_id, scheduled_at DESC);
CREATE INDEX idx_consultations_upcoming ON consultations (scheduled_at)
    WHERE status = 'scheduled';

-- Patient notes added by doctors
CREATE TABLE patient_notes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id  UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id   UUID NOT NULL REFERENCES care_team_members(id),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_patient_notes_patient ON patient_notes (patient_id, created_at DESC);

-- Doctor overrides on alerts
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS doctor_override TEXT;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS override_by UUID REFERENCES care_team_members(id);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS override_at TIMESTAMPTZ;
