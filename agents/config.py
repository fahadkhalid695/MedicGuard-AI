"""Configuration for the agent monitoring system."""

import os

from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mediguard:password@localhost:5432/mediguard")

# LLM model for orchestrator
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

# Patient IDs to monitor. Empty = subscribe to all via pattern.
_patient_ids_raw = os.getenv("PATIENT_IDS", "")
PATIENT_IDS: list[str] = [p.strip() for p in _patient_ids_raw.split(",") if p.strip()]

# Orchestrator settings
ORCHESTRATOR_WINDOW_SEC = float(os.getenv("ORCHESTRATOR_WINDOW_SEC", "5"))  # collect signals for N seconds before merging
ORCHESTRATOR_DEDUP_SEC = float(os.getenv("ORCHESTRATOR_DEDUP_SEC", "30"))   # suppress duplicate alerts within N seconds

# Twilio (for autonomous caregiver/patient contact)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

# Autonomous action settings
AUTONOMOUS_ACTIONS_ENABLED = os.getenv("AUTONOMOUS_ACTIONS_ENABLED", "true").lower() == "true"

# Thresholds (can be overridden via env or a config file)
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
    "window_size": 10,  # number of readings to analyze
    "hr_rise_per_reading": 3,  # avg increase per reading that signals deterioration
    "spo2_drop_per_reading": 0.3,
    "temp_rise_per_reading": 0.1,
    "bp_rise_per_reading": 3,
}
