"""Request/response models for the patient-facing API."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatientAlertRequest(BaseModel):
    """Request to send a patient-facing alert notification."""
    patient_id: str
    alert_id: str
    severity: Severity
    summary: str  # clinical summary from orchestrator
    action: str   # recommended clinical action


class PatientAlertResponse(BaseModel):
    """Response after sending patient notification."""
    patient_id: str
    alert_id: str
    patient_message: str  # the simplified message sent to patient
    channel: str          # "sms" or "push"
    delivered: bool
    dispatch_id: Optional[str] = None


class PatientResponseRequest(BaseModel):
    """Patient's reply to an alert notification."""
    patient_id: str
    alert_id: str
    response: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Patient's free-text response",
        examples=["I feel fine", "I feel worse", "I'm having chest pain"],
    )


class PatientResponseResult(BaseModel):
    """Result of processing a patient response."""
    response_id: str
    patient_id: str
    alert_id: str
    sentiment: str          # "positive", "negative", "neutral"
    feels_worse: bool
    action_taken: str       # what the system did in response
    timestamp: datetime
