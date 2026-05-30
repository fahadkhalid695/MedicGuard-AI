"""Configuration for the AlertDispatcher service."""

import os

from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mediguard:password@localhost:5432/mediguard")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DISPATCH_QUEUE = "queue:alert_dispatch"  # Redis list used as async queue

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

# SendGrid
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "alerts@mediguard.ai")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "MediGuard AI Alerts")

# Hospital endpoint
HOSPITAL_NOTIFY_URL = os.getenv("HOSPITAL_NOTIFY_URL", "http://hospital-system.local/api/notify")

# Dashboard
DASHBOARD_BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://localhost:3000")

# WebSocket
WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8765"))
