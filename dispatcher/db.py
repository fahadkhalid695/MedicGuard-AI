"""Database access for the dispatcher service."""

import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from dispatcher.config import DATABASE_URL
from dispatcher.models import (
    DeliveryStatus,
    DispatchChannel,
    DispatchRecord,
    PatientContext,
)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=3, max_size=15)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def fetch_patient_context(patient_id: str) -> Optional[PatientContext]:
    """
    Fetch patient name and assigned doctor/caregiver contact info.
    Returns None if patient not found.
    """
    pool = await get_pool()

    # Get patient info
    patient = await pool.fetchrow(
        "SELECT id, first_name, last_name FROM patients WHERE id = $1",
        uuid.UUID(patient_id),
    )
    if not patient:
        return None

    # Get assigned doctor (primary)
    doctor = await pool.fetchrow(
        """
        SELECT ctm.full_name, ctm.phone, ctm.email
        FROM patient_assignments pa
        JOIN care_team_members ctm ON ctm.id = pa.member_id
        WHERE pa.patient_id = $1
          AND pa.role = 'doctor'
          AND pa.unassigned_at IS NULL
          AND pa.is_primary = TRUE
        LIMIT 1
        """,
        uuid.UUID(patient_id),
    )

    # Get assigned caregiver
    caregiver = await pool.fetchrow(
        """
        SELECT ctm.full_name, ctm.phone
        FROM patient_assignments pa
        JOIN care_team_members ctm ON ctm.id = pa.member_id
        WHERE pa.patient_id = $1
          AND pa.role IN ('caregiver', 'nurse')
          AND pa.unassigned_at IS NULL
        LIMIT 1
        """,
        uuid.UUID(patient_id),
    )

    return PatientContext(
        patient_id=patient_id,
        first_name=patient["first_name"],
        last_name=patient["last_name"],
        full_name=f"{patient['first_name']} {patient['last_name']}",
        doctor_phone=doctor["phone"] if doctor else None,
        doctor_email=doctor["email"] if doctor else None,
        doctor_name=doctor["full_name"] if doctor else None,
        caregiver_phone=caregiver["phone"] if caregiver else None,
        caregiver_name=caregiver["full_name"] if caregiver else None,
    )


async def log_dispatch(
    alert_id: str,
    patient_id: str,
    channel: DispatchChannel,
    recipient: str,
    status: DeliveryStatus,
    message_preview: str = "",
    error_detail: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> str:
    """Log a dispatch attempt to the alert_dispatches table. Returns the dispatch ID."""
    pool = await get_pool()
    dispatch_id = uuid.uuid4()

    await pool.execute(
        """
        INSERT INTO alert_dispatches (id, alert_id, patient_id, channel, recipient, status, message_preview, error_detail, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        dispatch_id,
        uuid.UUID(alert_id),
        uuid.UUID(patient_id),
        channel.value,
        recipient,
        status.value,
        message_preview[:500] if message_preview else "",
        error_detail,
        metadata or {},
    )

    return str(dispatch_id)


async def update_dispatch_status(
    dispatch_id: str,
    status: DeliveryStatus,
    error_detail: Optional[str] = None,
) -> None:
    """Update the delivery status of a dispatch record."""
    pool = await get_pool()
    delivered_at = datetime.now(timezone.utc) if status == DeliveryStatus.DELIVERED else None

    await pool.execute(
        """
        UPDATE alert_dispatches
        SET status = $2, error_detail = $3, delivered_at = $4
        WHERE id = $1
        """,
        uuid.UUID(dispatch_id),
        status.value,
        error_detail,
        delivered_at,
    )
