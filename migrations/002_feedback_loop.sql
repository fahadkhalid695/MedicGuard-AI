-- MediGuard AI - Feedback & Evaluation Loop Schema
-- =================================================

-- ==========================================
-- 1. OUTCOME TRACKING
-- ==========================================
CREATE TYPE alert_outcome AS ENUM (
    'true_positive',       -- alert was correct, patient needed intervention
    'false_positive',      -- alert fired but patient was fine
    'true_negative',       -- no alert, patient was fine (tracked implicitly)
    'false_negative',      -- no alert fired but patient worsened (logged retroactively)
    'doctor_override',     -- doctor dismissed the alert as incorrect
    'patient_worsened',    -- patient condition deteriorated after alert
    'resolved_naturally'   -- condition resolved without intervention
);

CREATE TABLE alert_outcomes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id        UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    outcome         alert_outcome NOT NULL,
    agent_id        VARCHAR(100) NOT NULL,       -- which AI agent generated the alert
    condition_type  VARCHAR(100),                -- e.g. 'tachycardia', 'hypoxia'
    notes           TEXT,
    reviewed_by     UUID REFERENCES care_team_members(id),
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Context at time of outcome
    vitals_at_alert     JSONB,   -- snapshot when alert fired
    vitals_at_review    JSONB,   -- snapshot when outcome was recorded
    time_to_review_min  NUMERIC(8,2)  -- minutes between alert and review
);

CREATE INDEX idx_outcomes_alert ON alert_outcomes (alert_id);
CREATE INDEX idx_outcomes_agent ON alert_outcomes (agent_id, created_at DESC);
CREATE INDEX idx_outcomes_condition ON alert_outcomes (condition_type, created_at DESC);
CREATE INDEX idx_outcomes_time ON alert_outcomes (created_at DESC);

-- ==========================================
-- 2. AGENT PERFORMANCE (weekly aggregates)
-- ==========================================
CREATE TABLE agent_performance (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id            VARCHAR(100) NOT NULL,
    condition_type      VARCHAR(100),            -- NULL = aggregate across all conditions
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,

    -- Core metrics
    total_alerts        INTEGER NOT NULL DEFAULT 0,
    true_positives      INTEGER NOT NULL DEFAULT 0,
    false_positives     INTEGER NOT NULL DEFAULT 0,
    false_negatives     INTEGER NOT NULL DEFAULT 0,
    doctor_overrides    INTEGER NOT NULL DEFAULT 0,

    -- Calculated rates
    precision_rate      NUMERIC(5,4),   -- TP / (TP + FP)
    recall_rate         NUMERIC(5,4),   -- TP / (TP + FN)
    false_positive_rate NUMERIC(5,4),   -- FP / (FP + TN)
    f1_score            NUMERIC(5,4),   -- 2 * (precision * recall) / (precision + recall)

    -- Metadata
    ab_group            VARCHAR(10),    -- 'A', 'B', or NULL
    threshold_version   VARCHAR(50),    -- which threshold config was active
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (agent_id, condition_type, period_start, period_end, ab_group)
);

CREATE INDEX idx_perf_agent_time ON agent_performance (agent_id, period_start DESC);
CREATE INDEX idx_perf_condition ON agent_performance (condition_type, period_start DESC);
CREATE INDEX idx_perf_ab ON agent_performance (ab_group, period_start DESC) WHERE ab_group IS NOT NULL;

-- ==========================================
-- 3. THRESHOLD CONFIGURATIONS (versioned)
-- ==========================================
CREATE TABLE threshold_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version         VARCHAR(50) NOT NULL UNIQUE,
    agent_id        VARCHAR(100) NOT NULL,
    thresholds      JSONB NOT NULL,         -- full threshold config
    source          VARCHAR(50) NOT NULL DEFAULT 'manual',  -- 'manual', 'claude_suggested', 'ab_winner'
    is_active       BOOLEAN DEFAULT FALSE,
    ab_group        VARCHAR(10),            -- 'A' or 'B' if part of A/B test
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at    TIMESTAMPTZ,
    deactivated_at  TIMESTAMPTZ
);

CREATE INDEX idx_thresholds_active ON threshold_configs (agent_id) WHERE is_active = TRUE;
CREATE INDEX idx_thresholds_ab ON threshold_configs (ab_group) WHERE ab_group IS NOT NULL;

-- ==========================================
-- 4. A/B TEST CONFIGURATION
-- ==========================================
CREATE TABLE ab_tests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    agent_id        VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, running, completed, cancelled
    config_a_id     UUID NOT NULL REFERENCES threshold_configs(id),
    config_b_id     UUID NOT NULL REFERENCES threshold_configs(id),
    start_date      DATE,
    end_date        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Which patients are in which A/B group
CREATE TABLE ab_patient_groups (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ab_test_id  UUID NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,
    patient_id  UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    ab_group    VARCHAR(10) NOT NULL CHECK (ab_group IN ('A', 'B')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ab_test_id, patient_id)
);

CREATE INDEX idx_ab_groups_test ON ab_patient_groups (ab_test_id, ab_group);
CREATE INDEX idx_ab_groups_patient ON ab_patient_groups (patient_id);

-- ==========================================
-- 5. CLAUDE TUNING SUGGESTIONS LOG
-- ==========================================
CREATE TABLE tuning_suggestions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id            VARCHAR(100) NOT NULL,
    performance_data    JSONB NOT NULL,     -- input sent to Claude
    suggestion          JSONB NOT NULL,     -- Claude's response
    applied             BOOLEAN DEFAULT FALSE,
    applied_as_version  VARCHAR(50),        -- links to threshold_configs.version
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tuning_agent ON tuning_suggestions (agent_id, created_at DESC);
