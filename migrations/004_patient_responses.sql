-- MediGuard AI - Patient Responses Table
-- =======================================

CREATE TABLE patient_responses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    alert_id        UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    response_text   TEXT NOT NULL,
    sentiment       VARCHAR(20) NOT NULL,    -- 'positive', 'negative', 'neutral'
    feels_worse     BOOLEAN NOT NULL DEFAULT FALSE,
    responded_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by     UUID REFERENCES care_team_members(id),
    reviewed_at     TIMESTAMPTZ,
    notes           TEXT                     -- care team notes on the response
);

-- Fast lookup: responses for an alert
CREATE INDEX idx_patient_responses_alert ON patient_responses (alert_id, responded_at DESC);

-- Fast lookup: all responses from a patient
CREATE INDEX idx_patient_responses_patient ON patient_responses (patient_id, responded_at DESC);

-- Monitor escalations: patients who reported feeling worse
CREATE INDEX idx_patient_responses_worse ON patient_responses (responded_at DESC)
    WHERE feels_worse = TRUE;

-- Add 'sms_patient' to the dispatch_channel enum (for alert_dispatches table)
ALTER TYPE dispatch_channel ADD VALUE IF NOT EXISTS 'sms_patient';
