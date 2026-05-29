from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VitalsReading(BaseModel):
    """Incoming vitals reading from a sensor or device."""

    patient_id: UUID
    heart_rate: int = Field(..., description="Heart rate in bpm")
    bp_systolic: int = Field(..., description="Systolic blood pressure in mmHg")
    bp_diastolic: int = Field(..., description="Diastolic blood pressure in mmHg")
    spo2: float = Field(..., description="Blood oxygen saturation percentage")
    temperature: float = Field(..., description="Body temperature in Celsius")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("heart_rate")
    @classmethod
    def validate_heart_rate(cls, v: int) -> int:
        if not 20 <= v <= 300:
            raise ValueError("heart_rate must be between 20 and 300 bpm")
        return v

    @field_validator("bp_systolic")
    @classmethod
    def validate_bp_systolic(cls, v: int) -> int:
        if not 50 <= v <= 300:
            raise ValueError("bp_systolic must be between 50 and 300 mmHg")
        return v

    @field_validator("bp_diastolic")
    @classmethod
    def validate_bp_diastolic(cls, v: int) -> int:
        if not 30 <= v <= 200:
            raise ValueError("bp_diastolic must be between 30 and 200 mmHg")
        return v

    @field_validator("spo2")
    @classmethod
    def validate_spo2(cls, v: float) -> float:
        if not 50.0 <= v <= 100.0:
            raise ValueError("spo2 must be between 50 and 100 percent")
        return round(v, 1)

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 30.0 <= v <= 45.0:
            raise ValueError("temperature must be between 30.0 and 45.0 Celsius")
        return round(v, 1)


class VitalsResponse(BaseModel):
    """Response after successfully storing a vitals reading."""

    id: UUID
    patient_id: UUID
    heart_rate: int
    bp_systolic: int
    bp_diastolic: int
    spo2: float
    temperature: float
    timestamp: datetime
    cached: bool = True
    published: bool = True
