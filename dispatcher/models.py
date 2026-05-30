"""Data models for the AlertDispatcher service."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DispatchChannel(str, Enum):
    DB_LOG = "db_log"
    WEBSOCKET = "websocket"
    SMS_DOCTOR = "sms_doctor"
    SMS_CAREGIVER = "sms_caregiver"
    EMAIL = "email"
    HOSPITAL_NOTIFY = "hospital_notify"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class AgentSignal(BaseModel):
    agent: str
    patient_id: str
    severity: str
    reason: str
    recommended_action: str
    timestamp: str
    vitals_snapshot: Optional[dict] = None


class UnifiedAlert(BaseModel):
    """Unified alert received from the OrchestratorAgent."""
    patient_id: str
    overall_severity: Severity
    summary: str
    action: str
    confidence: float = Field(ge=0.0, le=1.0)
    agent_signals: list[AgentSignal]
    timestamp: datetime
    llm_model: str = ""


class PatientContext(BaseModel):
    """Patient info fetched from DB for notification content."""
    patient_id: str
    first_name: str
    last_name: str
    full_name: str = ""
    doctor_phone: Optional[str] = None
    doctor_email: Optional[str] = None
    doctor_name: Optional[str] = None
    caregiver_phone: Optional[str] = None
    caregiver_name: Optional[str] = None
    location: Optional[str] = None  # room/ward


class DispatchRecord(BaseModel):
    """Record of a single dispatch attempt."""
    id: Optional[str] = None
    alert_id: str
    patient_id: str
    channel: DispatchChannel
    recipient: str
    status: DeliveryStatus
    message_preview: str = ""
    error_detail: Optional[str] = None
    dispatched_at: datetime
