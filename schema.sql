-- MediGuard AI - PostgreSQL Database Schema
-- ==========================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================
-- PATIENTS
-- ==========================================
CREATE TABLE patients (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    date_of_birth   DATE NOT NULL,
    gender          VARCHAR(20),
    blood_type      VARCHAR(5),
    medical_history JSONB DEFAULT '[]',   -- past surgeries, hospitalizations, etc.
    conditions      TEXT[] DEFAULT '{}',   -- active diagnoses (e.g. 'Type 2 Diabetes')
    medications     JSONB DEFAULT '[]',   -- [{name, dosage, frequency, start_date}]
    emergency_contact JSONB,              -- {name, phone, relationship}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Age is calculated at query time (not stored) since CURRENT_DATE is not immutable:
-- SELECT *, EXTRACT(YEAR FROM age(CURRENT_DATE, date_of_birth))::INT AS age FROM patients;

CREATE INDEX idx_patients_name ON patients (last_name, first_name);

-- ==========================================
-- CARE TEAM (Doctors & Caregivers)
-- ==========================================
CREATE TYPE care_role AS ENUM ('doctor', 'nurse', 'caregiver', 'specialist');

CREATE TABLE care_team_members (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name   VARCHAR(200) NOT NULL,
    role        care_role NOT NULL,
    specialty   VARCHAR(100),
    email       VARCHAR(255) UNIQUE,
    phone       VARCHAR(30),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Junction table: which care team members are assigned to which patients
CREATE TABLE patient_assignments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    member_id       UUID NOT NULL REFERENCES care_team_members(id) ON DELETE CASCADE,
    role            care_role NOT NULL,
    is_primary      BOOLEAN DEFAULT FALSE,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    unassigned_at   TIMESTAMPTZ,
    UNIQUE (patient_id, member_id, role)
);

CREATE INDEX idx_assignments_patient ON patient_assignments (patient_id) WHERE unassigned_at IS NULL;
CREATE INDEX idx_assignments_member  ON patient_assignments (member_id) WHERE unassigned_at IS NULL;

-- ==========================================
-- VITALS (Time-Series)
-- ==========================================
CREATE TABLE vitals (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    recorded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    heart_rate        SMALLINT,          -- bpm
    systolic_bp       SMALLINT,          -- mmHg
    diastolic_bp      SMALLINT,          -- mmHg
    spo2              NUMERIC(5,2),      -- percentage
    temperature       NUMERIC(4,1),      -- Celsius
    respiratory_rate  SMALLINT,          -- breaths per minute

    source            VARCHAR(50) DEFAULT 'sensor',  -- sensor, manual, device_model
    metadata          JSONB DEFAULT '{}'
);

-- Primary time-series index: fast range queries per patient
CREATE INDEX idx_vitals_patient_time ON vitals (patient_id, recorded_at DESC);

-- Covering index for dashboard queries (avoids heap lookups)
CREATE INDEX idx_vitals_latest ON vitals (patient_id, recorded_at DESC)
    INCLUDE (heart_rate, systolic_bp, diastolic_bp, spo2, temperature, respiratory_rate);

-- Global time-based index for batch analytics
CREATE INDEX idx_vitals_time ON vitals (recorded_at DESC);

-- ==========================================
-- ALERT LOGS
-- ==========================================
CREATE TYPE alert_severity AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE alert_status   AS ENUM ('active', 'acknowledged', 'resolved', 'dismissed');

CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    severity        alert_severity NOT NULL,
    status          alert_status NOT NULL DEFAULT 'active',
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    vital_snapshot  JSONB,              -- vitals at time of alert
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    acknowledged_by UUID REFERENCES care_team_members(id),
    resolved_by     UUID REFERENCES care_team_members(id)
);

-- Fast lookup of active/critical alerts per patient
CREATE INDEX idx_alerts_patient_active ON alerts (patient_id, triggered_at DESC)
    WHERE status = 'active';

-- Dashboard: all unresolved alerts by severity
CREATE INDEX idx_alerts_severity_active ON alerts (severity, triggered_at DESC)
    WHERE status IN ('active', 'acknowledged');

-- Time-range queries for alert history
CREATE INDEX idx_alerts_time ON alerts (triggered_at DESC);

-- ==========================================
-- HELPER: auto-update updated_at
-- ==========================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
