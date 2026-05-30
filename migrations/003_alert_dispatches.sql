-- MediGuard AI - Alert Dispatches Table
-- ======================================

CREATE TYPE dispatch_channel AS ENUM (
    'db_log',
    'websocket',
    'sms_doctor',
    'sms_caregiver',
    'email',
    'hospital_notify'
);

CREATE TYPE delivery_status AS ENUM (
    'pending',
    'sent',
    'delivered',
    'failed'
);

CREATE TABLE alert_dispatches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id        UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    channel         dispatch_channel NOT NULL,
    recipient       VARCHAR(255) NOT NULL,       -- phone number, email, endpoint URL, or "system"
    status          delivery_status NOT NULL DEFAULT 'pending',
    message_preview TEXT,                        -- first 500 chars of the message sent
    error_detail    TEXT,                        -- error message if failed
    dispatched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at    TIMESTAMPTZ,
    retry_count     SMALLINT DEFAULT 0,
    metadata        JSONB DEFAULT '{}'           -- provider message IDs, response codes, etc.
);

-- Fast lookup: all dispatches for an alert
CREATE INDEX idx_dispatches_alert ON alert_dispatches (alert_id);

-- Fast lookup: dispatch history for a patient
CREATE INDEX idx_dispatches_patient ON alert_dispatches (patient_id, dispatched_at DESC);

-- Monitor failed deliveries
CREATE INDEX idx_dispatches_failed ON alert_dispatches (status, dispatched_at DESC)
    WHERE status = 'failed';

-- Recent dispatches by channel (for monitoring dashboard)
CREATE INDEX idx_dispatches_channel ON alert_dispatches (channel, dispatched_at DESC);
