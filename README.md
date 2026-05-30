# MediGuard AI

**Intelligent Patient Monitoring & Clinical Decision Support Platform**

MediGuard AI is a real-time patient monitoring system powered by multi-agent AI. It ingests vitals from sensors, runs them through specialist AI agents for anomaly detection, synthesizes findings via an LLM-powered orchestrator, and dispatches alerts through multiple channels — all while maintaining a feedback loop for continuous accuracy improvement.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Services](#services)
5. [Data Flow](#data-flow)
6. [Database Schema](#database-schema)
7. [Setup Guide](#setup-guide)
8. [Running the System](#running-the-system)
9. [Configuration Reference](#configuration-reference)
10. [API Reference](#api-reference)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SENSOR / DEVICE LAYER                               │
│                    (Wearables, Hospital Monitors, IoT)                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ POST /api/vitals
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      VITALS INGESTION SERVICE (FastAPI)                       │
│  • Validates ranges • Persists to PostgreSQL • Caches in Redis • Pub/Sub     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ Redis Pub/Sub: vitals:{patient_id}
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MULTI-AGENT MONITORING LAYER (Python)                    │
│                                                                              │
│  ┌──────────────┐ ┌────────────────┐ ┌─────────────┐ ┌──────────────┐      │
│  │CardiacAgent  │ │RespiratoryAgent│ │ThermalAgent  │ │ TrendAgent   │      │
│  │HR, BP        │ │SpO2, RR       │ │Temperature   │ │Slope analysis│      │
│  └──────┬───────┘ └───────┬───────┘ └──────┬──────┘ └──────┬───────┘      │
│         └──────────────────┴────────────────┴───────────────┘               │
│                            │ Redis: agent_signals:{patient_id}               │
│                            ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    ORCHESTRATOR AGENT                                  │   │
│  │  • Collects signals (5s window) • Deduplicates • Calls Claude LLM    │   │
│  │  • Computes confidence score • Persists unified alert                 │   │
│  │  • Executes autonomous actions (tools) based on severity              │   │
│  └──────────────────────────────────┬───────────────────────────────────┘   │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │ Redis Queue: queue:alert_dispatch
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ALERT DISPATCHER SERVICE (Python)                        │
│                                                                              │
│  Severity Routing:                                                           │
│  • LOW      → DB log only                                                   │
│  • MEDIUM   → WebSocket to doctor dashboard                                 │
│  • HIGH     → SMS (doctor) + WebSocket + Patient SMS                        │
│  • CRITICAL → SMS (doctor+caregiver) + Email + Hospital POST + Patient SMS  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Doctor Dashboard │  │  Patient API     │  │ Admin Dashboard  │
│ (React+Tailwind) │  │  (FastAPI)       │  │ (React+Recharts) │
│ Live vitals,     │  │  Simplified SMS, │  │ Agent accuracy,  │
│ AI insights,     │  │  Patient replies,│  │ A/B tests,       │
│ Doctor actions   │  │  Re-trigger loop │  │ Threshold tuning │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Database** | PostgreSQL 15+ | Patient records, vitals history, alerts, audit logs |
| **Cache/Queue** | Redis 7+ | Real-time vitals cache, Pub/Sub, async job queues |
| **Vitals Ingestion** | Python, FastAPI, asyncpg | High-throughput vitals API with validation |
| **AI Agents** | Python, LangChain, Redis Pub/Sub | Multi-agent anomaly detection |
| **LLM** | Claude (Anthropic API) | Alert synthesis, threshold tuning, patient messaging |
| **Orchestrator** | Python, LangChain Tools | Signal merging, autonomous actions |
| **Dispatcher** | Python, Twilio, SendGrid, WebSockets | Multi-channel alert routing |
| **Doctor Dashboard** | React 18, TypeScript, Tailwind CSS, Recharts | Real-time clinical UI |
| **Admin Dashboard** | React 18, TypeScript, Recharts | Performance analytics |
| **Patient API** | Python, FastAPI, Anthropic SDK | Patient-facing notifications |
| **Feedback Backend** | Node.js, Express, TypeScript | Weekly/monthly jobs, A/B testing |

---

## Project Structure

```
MediGuard AI/
├── schema.sql                    # Core PostgreSQL schema
├── redis-schema.md               # Redis caching design
├── migrations/                   # Incremental DB migrations
│   ├── 002_feedback_loop.sql     # Outcome tracking, agent performance, A/B tests
│   ├── 003_alert_dispatches.sql  # Notification dispatch logging
│   ├── 004_patient_responses.sql # Patient reply tracking
│   ├── 005_consultations_and_notes.sql  # Doctor consultations & notes
│   └── 006_agent_actions.sql     # Autonomous action audit log
│
├── vitals-service/               # FastAPI vitals ingestion
│   ├── app/
│   │   ├── main.py              # App entry point
│   │   ├── routes.py            # POST /vitals, GET /vitals/:id/latest
│   │   ├── models.py            # Pydantic models with validation
│   │   ├── db.py                # asyncpg connection pool
│   │   ├── redis_client.py      # Redis async client
│   │   └── config.py            # Environment settings
│   ├── mock_generator.py        # Simulates 10 patients with anomalies
│   └── requirements.txt
│
├── agents/                       # Multi-agent monitoring system
│   ├── main.py                  # Entry point (runs all agents)
│   ├── base_agent.py            # Abstract base with Pub/Sub subscription
│   ├── cardiac_agent.py         # Heart rate & blood pressure
│   ├── respiratory_agent.py     # SpO2 & respiratory rate
│   ├── thermal_agent.py         # Body temperature
│   ├── trend_agent.py           # Sliding window slope analysis
│   ├── orchestrator_agent.py    # LLM synthesis + autonomous actions
│   ├── models.py                # Shared Pydantic models
│   ├── config.py                # All thresholds & settings
│   ├── tools/
│   │   ├── definitions.py       # LangChain tool definitions
│   │   └── autonomous_executor.py  # Severity-based action engine
│   └── requirements.txt
│
├── dispatcher/                   # Alert routing service
│   ├── main.py                  # Entry point
│   ├── dispatcher.py            # Core routing logic
│   ├── db.py                    # Patient context & dispatch logging
│   ├── models.py                # Dispatch models
│   ├── channels/
│   │   ├── sms.py              # Twilio SMS
│   │   ├── email.py            # SendGrid email
│   │   ├── websocket.py        # WebSocket server for dashboards
│   │   ├── hospital.py         # HTTP POST to hospital
│   │   └── patient_notify.py   # Patient-facing API integration
│   └── requirements.txt
│
├── patient-api/                  # Patient-facing alert service
│   ├── app/
│   │   ├── main.py             # FastAPI app
│   │   ├── routes.py           # POST /patient-alert, POST /patient-response
│   │   ├── llm.py              # Claude: simplify alerts + analyze sentiment
│   │   ├── sms.py              # Twilio patient SMS
│   │   ├── db.py               # Patient data access
│   │   └── models.py           # Request/response schemas
│   └── requirements.txt
│
├── doctor-dashboard/             # Doctor-facing React dashboard
│   ├── src/
│   │   ├── App.tsx             # Main app with WebSocket state
│   │   ├── api.ts              # REST API client
│   │   ├── types.ts            # TypeScript interfaces
│   │   ├── utils.ts            # Formatting helpers
│   │   ├── components/
│   │   │   ├── PatientList.tsx       # Sidebar with severity badges
│   │   │   ├── PatientDetail.tsx     # Main patient view
│   │   │   ├── VitalsCards.tsx       # Live vital sign cards
│   │   │   ├── VitalsChart.tsx       # Recharts trend charts
│   │   │   ├── AIInsightPanel.tsx    # Orchestrator summary
│   │   │   ├── AlertTimeline.tsx     # 24h alert history
│   │   │   ├── DoctorActionPanel.tsx # Acknowledge, override, escalate
│   │   │   ├── ConsultModal.tsx      # Schedule consultation modal
│   │   │   └── NotificationBar.tsx   # Critical alert banner + sound
│   │   └── hooks/
│   │       ├── useWebSocket.ts       # Auto-reconnecting WS
│   │       └── useAlertSound.ts      # Web Audio API alert tone
│   └── package.json
│
├── dashboard/                    # Admin performance dashboard
│   ├── src/
│   │   ├── App.tsx             # Agent selector + charts
│   │   ├── api.ts              # Performance API client
│   │   └── components/
│   │       ├── AccuracyTrendsChart.tsx  # Precision/Recall/F1
│   │       ├── FalsePositiveChart.tsx   # FP rate with target line
│   │       ├── ABComparisonPanel.tsx    # A/B test comparison
│   │       └── SummaryCards.tsx         # KPI cards
│   └── package.json
│
└── backend/                      # Feedback loop backend (Node.js)
    ├── src/
    │   ├── server.ts            # Express + cron scheduling
    │   ├── db.ts                # PostgreSQL pool
    │   ├── types.ts             # TypeScript types
    │   ├── routes/feedback.ts   # REST API for outcomes, A/B, thresholds
    │   ├── services/
    │   │   ├── outcome-tracking.ts  # Record alert outcomes
    │   │   └── ab-testing.ts        # A/B test management
    │   └── jobs/
    │       ├── weekly-accuracy-report.ts   # Precision/recall calculation
    │       └── monthly-threshold-tuning.ts # Claude-powered tuning
    └── package.json
```

---

## Services

### 1. Vitals Ingestion Service

**Port:** 8000 | **Language:** Python/FastAPI

Accepts real-time vitals from sensors/devices. Each reading is:
- Validated against clinical ranges (HR 20-300, SpO2 50-100, etc.)
- Persisted to PostgreSQL `vitals` table
- Cached in Redis hash with 60s TTL
- Published to Redis Pub/Sub channel `vitals:{patient_id}`

**Key endpoints:**
- `POST /api/vitals` — Ingest a reading
- `GET /api/vitals/{patient_id}/latest` — Get cached latest

---

### 2. Multi-Agent Monitoring System

**Language:** Python | **Framework:** LangChain + asyncio

Four specialist agents run concurrently, each subscribing to vitals via Redis Pub/Sub:

| Agent | Monitors | Thresholds |
|-------|----------|------------|
| **CardiacAgent** | Heart rate, blood pressure | Tachycardia >100, bradycardia <50, hypertensive crisis >180 systolic |
| **RespiratoryAgent** | SpO2, respiratory rate | Hypoxia <92%, critical <88%, tachypnea >25/min |
| **ThermalAgent** | Temperature | Fever >38.5°C, hypothermia <35°C |
| **TrendAgent** | All vitals (sliding window) | Linear regression slope over last 10 readings |

Each agent outputs a structured `RiskAssessment`:
```json
{
  "agent": "CardiacAgent",
  "patient_id": "uuid",
  "severity": "high",
  "reason": "Tachycardia detected: 155 bpm",
  "recommended_action": "12-lead ECG stat...",
  "vitals_snapshot": {"heart_rate": 155, "bp_systolic": 142}
}
```

---

### 3. Orchestrator Agent

**Language:** Python | **LLM:** Claude (Anthropic)

Sits above the specialist agents. For each patient:
1. **Collects** signals within a 5-second window
2. **Deduplicates** — keeps highest severity per agent
3. **Calls Claude** with all signals to produce a unified summary
4. **Computes confidence** (0-1) based on agent agreement
5. **Persists** the unified alert to PostgreSQL
6. **Dispatches** to the alert queue
7. **Executes autonomous actions** based on severity rules

**Autonomous Tool-Use (LangChain):**

| Severity | Allowed Actions |
|----------|----------------|
| LOW | None |
| MEDIUM | contact_caregiver |
| HIGH | schedule_consultation + contact_caregiver |
| CRITICAL | All 4 tools simultaneously |

Tools: `schedule_consultation`, `notify_hospital`, `contact_caregiver`, `request_patient_checkin`

---

### 4. Alert Dispatcher

**Port:** 8765 (WebSocket) | **Language:** Python

Consumes unified alerts from Redis queue and routes by severity:

| Severity | Channels |
|----------|----------|
| LOW | DB log only |
| MEDIUM | WebSocket → doctor dashboard |
| HIGH | SMS (doctor) + WebSocket + Patient SMS |
| CRITICAL | SMS (doctor + caregiver) + Email + Hospital POST + Patient SMS |

Every dispatch is logged to `alert_dispatches` with delivery status tracking.

---

### 5. Patient API

**Port:** 8001 | **Language:** Python/FastAPI

Patient-facing service that:
- Generates simplified, non-medical alert messages via Claude
- Sends SMS to patients for HIGH/CRITICAL alerts
- Accepts patient responses ("I feel fine" / "I feel worse")
- Analyzes sentiment and re-triggers agent analysis if patient reports worsening

---

### 6. Doctor Dashboard

**Port:** 3000 | **Framework:** React + Tailwind CSS + Recharts

Real-time clinical interface with:
- Patient list sidebar (severity-sorted, color-coded)
- Live vitals cards with threshold-based coloring
- 30-minute trend charts (4 panels: HR+SpO2, BP, Temp, RR)
- AI Insight panel (orchestrator summary + recommended action)
- Alert timeline (last 24 hours)
- Doctor Action Panel (acknowledge, override, escalate, schedule consult, notes)
- Critical alert notification bar with audio alert

---

### 7. Admin Dashboard

**Port:** 3000 (separate) | **Framework:** React + Recharts

Performance analytics for system administrators:
- Precision/Recall/F1 trends over time
- False positive rate with target threshold line
- A/B test comparison (side-by-side metrics + charts)
- Per-agent and per-condition breakdowns

---

### 8. Feedback Backend

**Port:** 3001 | **Framework:** Node.js + Express + TypeScript

Manages the continuous improvement loop:
- **Outcome tracking** — Records true/false positives, doctor overrides
- **Weekly accuracy report** (Mon 2AM) — Calculates precision, recall, FPR
- **Monthly threshold tuning** (1st of month 3AM) — Calls Claude for suggestions
- **A/B testing** — Run two threshold configs simultaneously
- **Threshold management** — Version, activate, deactivate configs

---

## Data Flow

### Vitals Ingestion Flow

```
Sensor → POST /api/vitals → Validate → PostgreSQL (persist)
                                      → Redis Hash (cache, TTL 60s)
                                      → Redis Pub/Sub (real-time)
```

### Alert Generation Flow

```
Redis Pub/Sub → 4 Specialist Agents (concurrent)
                    │
                    ▼ (publish to agent_signals:{patient_id})
              Orchestrator Agent
                    │
                    ├── Claude LLM → Unified summary + severity
                    ├── Confidence score calculation
                    ├── PostgreSQL (persist alert)
                    ├── Redis Queue (dispatch)
                    └── Autonomous Actions (tools)
```

### Alert Dispatch Flow

```
Redis Queue → Dispatcher → Route by severity
                              │
                              ├── DB Log (always)
                              ├── WebSocket → Doctor Dashboard
                              ├── Twilio SMS → Doctor / Caregiver
                              ├── SendGrid Email → Doctor
                              ├── HTTP POST → Hospital System
                              └── Patient API → Patient SMS
```

### Patient Response Flow

```
Patient SMS reply → POST /patient-response
                        │
                        ├── Claude sentiment analysis
                        ├── Store in patient_responses table
                        │
                        └── If "feels worse":
                              → Publish PatientSelfReport signal
                              → Orchestrator re-evaluates
                              → New alert cycle begins
```

### Feedback Loop Flow

```
Doctor reviews alert → Records outcome (true/false positive, override)
                            │
                            ▼
Weekly Job → Calculate precision/recall/FPR per agent
                            │
                            ▼
Monthly Job → Send performance data to Claude
           → Receive threshold suggestions
           → Store as new config (requires admin approval)
                            │
                            ▼
A/B Test → Split patients → Compare configs → Promote winner
```

---

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `patients` | Patient profiles (name, DOB, conditions, medications) |
| `care_team_members` | Doctors, nurses, caregivers |
| `patient_assignments` | Many-to-many: who's assigned to whom |
| `vitals` | Time-series vitals readings |
| `alerts` | Unified alerts with severity, status, AI summary |

### Feedback & Performance Tables

| Table | Purpose |
|-------|---------|
| `alert_outcomes` | True/false positive tracking per alert |
| `agent_performance` | Weekly aggregated metrics per agent |
| `threshold_configs` | Versioned threshold configurations |
| `ab_tests` | A/B test definitions |
| `ab_patient_groups` | Patient group assignments for A/B |
| `tuning_suggestions` | Claude's threshold suggestions log |

### Dispatch & Action Tables

| Table | Purpose |
|-------|---------|
| `alert_dispatches` | Every notification sent (channel, status, recipient) |
| `patient_responses` | Patient replies with sentiment analysis |
| `agent_actions` | Autonomous action audit log |
| `consultations` | Scheduled emergency consultations |
| `patient_notes` | Doctor notes on patient records |

### Key Indexes

- `idx_vitals_patient_time` — Fast per-patient time-range queries
- `idx_vitals_latest` — Covering index for dashboard (avoids heap)
- `idx_alerts_patient_active` — Partial index on active alerts only
- `idx_alerts_severity_active` — Unresolved alerts by severity
- `idx_agent_actions_patient` — Action audit per patient

---

## Setup Guide

### Prerequisites

- **Python 3.11+** with pip
- **Node.js 18+** with npm
- **PostgreSQL 15+**
- **Redis 7+**
- **Anthropic API key** (for Claude)
- **Twilio account** (optional, for SMS)
- **SendGrid account** (optional, for email)

### 1. Database Setup

```bash
# Create the database
createdb mediguard

# Run the core schema
psql mediguard < schema.sql

# Run migrations in order
psql mediguard < migrations/002_feedback_loop.sql
psql mediguard < migrations/003_alert_dispatches.sql
psql mediguard < migrations/004_patient_responses.sql
psql mediguard < migrations/005_consultations_and_notes.sql
psql mediguard < migrations/006_agent_actions.sql
```

### 2. Redis

```bash
# Start Redis (default port 6379)
redis-server
```

### 3. Vitals Ingestion Service

```bash
cd vitals-service
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DATABASE_URL and REDIS_URL

uvicorn app.main:app --port 8000 --reload
```

### 4. Multi-Agent System

```bash
cd agents
pip install -r requirements.txt
cp .env.example .env
# Edit .env: REDIS_URL, DATABASE_URL, ANTHROPIC_API_KEY

python -m agents
```

### 5. Alert Dispatcher

```bash
cd dispatcher
pip install -r requirements.txt
cp .env.example .env
# Edit .env: DATABASE_URL, REDIS_URL, TWILIO_*, SENDGRID_*

python -m dispatcher
```

### 6. Patient API

```bash
cd patient-api
pip install -r requirements.txt
cp .env.example .env
# Edit .env: DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY, TWILIO_*

uvicorn app.main:app --port 8001 --reload
```

### 7. Doctor Dashboard

```bash
cd doctor-dashboard
npm install
npm run dev
# Opens at http://localhost:3000
```

### 8. Admin Dashboard

```bash
cd dashboard
npm install
npm run dev
# Opens at http://localhost:3000 (use different port if doctor-dashboard is running)
```

### 9. Feedback Backend

```bash
cd backend
npm install
npm run dev
# Runs at http://localhost:3001
```

### 10. Mock Data Generator

```bash
cd vitals-service
python mock_generator.py
# Simulates 10 patients, sends readings every 2s, injects anomalies ~8%
```

---

## Running the System

### Recommended Startup Order

```bash
# 1. Infrastructure
redis-server
pg_ctl start  # or your PostgreSQL service

# 2. Core services (each in its own terminal)
cd vitals-service && uvicorn app.main:app --port 8000
cd agents && python -m agents
cd dispatcher && python -m dispatcher
cd patient-api && uvicorn app.main:app --port 8001
cd backend && npm run dev

# 3. Frontends
cd doctor-dashboard && npm run dev
cd dashboard && npm run dev

# 4. Generate test data
cd vitals-service && python mock_generator.py
```

### Service Ports

| Service | Port | Protocol |
|---------|------|----------|
| Vitals Ingestion | 8000 | HTTP |
| Patient API | 8001 | HTTP |
| Feedback Backend | 3001 | HTTP |
| Doctor Dashboard | 3000 | HTTP |
| Admin Dashboard | 3002 | HTTP |
| WebSocket (Dispatcher) | 8765 | WS |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |

---

## Configuration Reference

### Environment Variables

#### Vitals Service (`vitals-service/.env`)
```
DATABASE_URL=postgresql://mediguard:password@localhost:5432/mediguard
REDIS_URL=redis://localhost:6379/0
VITALS_CACHE_TTL=60
```

#### Agents (`agents/.env`)
```
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://mediguard:password@localhost:5432/mediguard
LLM_MODEL=claude-sonnet-4-20250514
PATIENT_IDS=                          # empty = monitor all
ORCHESTRATOR_WINDOW_SEC=5
ORCHESTRATOR_DEDUP_SEC=30
AUTONOMOUS_ACTIONS_ENABLED=true
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

#### Dispatcher (`dispatcher/.env`)
```
DATABASE_URL=postgresql://mediguard:password@localhost:5432/mediguard
REDIS_URL=redis://localhost:6379/0
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+15551234567
SENDGRID_API_KEY=SG.xxxxxxxx
SENDGRID_FROM_EMAIL=alerts@mediguard.ai
HOSPITAL_NOTIFY_URL=http://hospital-system.local/api/notify
DASHBOARD_BASE_URL=http://localhost:3000
WS_HOST=0.0.0.0
WS_PORT=8765
```

#### Patient API (`patient-api/.env`)
```
DATABASE_URL=postgresql://mediguard:password@localhost:5432/mediguard
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+15551234567
DASHBOARD_BASE_URL=http://localhost:3000
PORT=8001
```

### Agent Thresholds (configurable in `agents/config.py`)

```python
CARDIAC_THRESHOLDS = {
    "tachycardia_bpm": 100,
    "bradycardia_bpm": 50,
    "hypertensive_systolic": 180,
    "hypertensive_diastolic": 120,
    "hypotensive_systolic": 90,
}

RESPIRATORY_THRESHOLDS = {
    "hypoxia_spo2": 92.0,
    "critical_spo2": 88.0,
    "tachypnea_rate": 25,
    "bradypnea_rate": 8,
}

THERMAL_THRESHOLDS = {
    "fever_temp": 38.5,
    "high_fever_temp": 39.5,
    "hypothermia_temp": 35.0,
    "severe_hypothermia_temp": 33.0,
}

TREND_THRESHOLDS = {
    "window_size": 10,
    "hr_rise_per_reading": 3,
    "spo2_drop_per_reading": 0.3,
    "temp_rise_per_reading": 0.1,
    "bp_rise_per_reading": 3,
}
```

---

## API Reference

### Vitals Service (port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/vitals` | Ingest a vitals reading |
| GET | `/api/vitals/{patient_id}/latest` | Get cached latest vitals |
| GET | `/api/health` | Health check |

### Patient API (port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/patient-alert` | Send simplified alert to patient |
| POST | `/api/patient-response` | Patient replies to alert |
| GET | `/api/patient-alert/{patient_id}/latest` | Get latest alert for patient |

### Feedback Backend (port 3001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/feedback/outcomes` | Record alert outcome |
| GET | `/api/feedback/outcomes/alert/:id` | Get outcomes for an alert |
| GET | `/api/feedback/performance/:agentId/trends` | Performance trends |
| GET | `/api/feedback/performance/summary` | All agents summary |
| POST | `/api/feedback/ab-tests` | Create A/B test |
| POST | `/api/feedback/ab-tests/:id/assign` | Assign patients to groups |
| POST | `/api/feedback/ab-tests/:id/start` | Start A/B test |
| POST | `/api/feedback/ab-tests/:id/complete` | Complete with winner |
| GET | `/api/feedback/ab-tests/:id/results` | Get comparison results |
| GET | `/api/feedback/thresholds` | List all threshold configs |
| POST | `/api/feedback/thresholds/:id/activate` | Activate a config |
| GET | `/api/feedback/tuning-suggestions` | Get Claude suggestions |

### Doctor Dashboard API (expected by frontend)

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/api/alerts/:id` | Acknowledge, override alert |
| POST | `/api/alerts/:id/escalate` | Manual escalation |
| POST | `/api/consultations` | Schedule consultation |
| POST | `/api/patients/:id/notes` | Add patient note |

---

## Redis Schema

### Real-Time Cache

| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `vitals:latest:{patient_id}` | Hash | 60s | Latest vitals snapshot |
| `alert:active:{patient_id}` | String | 3600s | Active alert cache |
| `patients:connected` | Set | — | Currently monitored patients |

### Pub/Sub Channels

| Channel | Publisher | Subscribers |
|---------|-----------|-------------|
| `vitals:{patient_id}` | Vitals Service | All 4 specialist agents |
| `agent_signals:{patient_id}` | Specialist agents | Orchestrator |

### Queues (Redis Lists)

| Queue | Producer | Consumer |
|-------|----------|----------|
| `queue:alert_dispatch` | Orchestrator | Dispatcher |
| `queue:caregiver_sms` | Autonomous tools | SMS worker |
| `queue:patient_checkin` | Autonomous tools | Patient API |
| `queue:patient_escalations` | Patient API | Care team |

### Streams

| Stream | Purpose |
|--------|---------|
| `stream:vitals:{patient_id}` | Short-term replay buffer (~1000 readings) |

---

## Confidence Score Calculation

The orchestrator computes a confidence score (0-1) for each unified alert:

```
confidence = (0.4 × coverage) + (0.6 × agreement)

coverage  = reporting_agents / 4
agreement = 1 - avg(|agent_severity - overall_severity| / max_distance)
```

- **1 agent reporting** → max confidence 0.7
- **All 4 agents agreeing on CRITICAL** → confidence ~1.0
- **2 agents disagreeing (HIGH vs MEDIUM)** → confidence ~0.6

---

## Autonomous Action Rules

The orchestrator can take actions without human approval:

| Severity | Actions | Rationale |
|----------|---------|-----------|
| LOW | None | No intervention needed |
| MEDIUM | Contact caregiver | Inform, don't escalate |
| HIGH | Schedule consult + contact caregiver | Ensure medical follow-up |
| CRITICAL | All 4 tools simultaneously | Life-threatening, no time to wait |

**Kill switch:** Set `AUTONOMOUS_ACTIONS_ENABLED=false` to disable.

Every autonomous action is logged to `agent_actions` for full audit trail.

---

## Feedback Loop Details

### Weekly Accuracy Report (Monday 2:00 AM)

Calculates per agent and per condition type:
- **Precision** = TP / (TP + FP)
- **Recall** = TP / (TP + FN)
- **False Positive Rate** = FP / (FP + TP)
- **F1 Score** = 2 × (P × R) / (P + R)

Doctor overrides count as false positives.

### Monthly Threshold Tuning (1st of month, 3:00 AM)

1. Gathers 30 days of performance data
2. Sends to Claude with current thresholds
3. Claude suggests adjustments following rules:
   - Critical thresholds stay conservative (high sensitivity)
   - Non-critical can be relaxed if FPR is high
   - Precision < 0.7 → widen normal range
   - Recall < 0.9 → tighten thresholds
   - Override rate > 20% → thresholds too aggressive
4. Suggestion stored (inactive) — requires admin approval

### A/B Testing

1. Create two threshold configs (A = control, B = experiment)
2. Randomly split patients 50/50
3. `getThresholdForPatient()` returns correct config per group
4. Run for N weeks, compare metrics
5. Promote winner or roll back

---

## Security Considerations

- All API keys stored in `.env` files (gitignored)
- Database credentials never hardcoded
- Patient data encrypted at rest (PostgreSQL TDE recommended)
- WebSocket connections authenticated via doctor_id registration
- SMS/email contain no raw medical data beyond summary
- Audit trail for every autonomous action and notification

---

## License

Proprietary — MediGuard AI © 2024-2026
