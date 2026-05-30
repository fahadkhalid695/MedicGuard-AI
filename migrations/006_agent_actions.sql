-- MediGuard AI - Agent Autonomous Actions Log
-- =============================================

CREATE TABLE agent_actions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type     VARCHAR(50) NOT NULL,       -- schedule_consultation, notify_hospital, contact_caregiver, request_patient_checkin
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    alert_id        UUID REFERENCES alerts(id) ON DELETE SET NULL,
    triggered_by    VARCHAR(100) NOT NULL,       -- agent name (e.g. 'OrchestratorAgent')
    severity        VARCHAR(20) NOT NULL,        -- severity that triggered this action
    input_params    JSONB DEFAULT '{}',          -- parameters passed to the tool
    outcome         VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, success, failed, skipped
    outcome_detail  TEXT,                        -- response or error message
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast lookup: actions for a patient
CREATE INDEX idx_agent_actions_patient ON agent_actions (patient_id, timestamp DESC);

-- Fast lookup: actions by type
CREATE INDEX idx_agent_actions_type ON agent_actions (action_type, timestamp DESC);

-- Monitor failures
CREATE INDEX idx_agent_actions_failed ON agent_actions (timestamp DESC)
    WHERE outcome = 'failed';

-- Audit: all actions by a specific agent
CREATE INDEX idx_agent_actions_agent ON agent_actions (triggered_by, timestamp DESC);
