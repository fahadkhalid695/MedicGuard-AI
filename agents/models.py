"""Shared data models for the multi-agent monitoring system."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    NORMAL = "normal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Numeric ordering for severity comparison
SEVERITY_ORDER: dict[Severity, int] = {
    Severity.NORMAL: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class RiskAssessment(BaseModel):
    """Structured output from each monitoring agent."""

    agent: str
    patient_id: str
    severity: Severity
    reason: str
    recommended_action: str
    timestamp: datetime
    vitals_snapshot: Optional[dict] = None

    def is_alert(self) -> bool:
        return self.severity in (Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL)


class VitalsReading(BaseModel):
    """A single vitals reading received from Redis Pub/Sub."""

    id: Optional[str] = None
    patient_id: str
    heart_rate: int
    bp_systolic: int
    bp_diastolic: int
    spo2: float
    temperature: float
    respiratory_rate: Optional[int] = None
    timestamp: str


class UnifiedAlert(BaseModel):
    """
    Unified alert produced by the OrchestratorAgent after merging
    all specialist agent signals and consulting the LLM.
    """

    patient_id: str
    overall_severity: Severity
    summary: str
    action: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="0-1 confidence based on agent agreement")
    agent_signals: list[RiskAssessment]
    timestamp: datetime
    llm_model: str = ""
