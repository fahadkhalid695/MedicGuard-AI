"""Database access for the patient-facing API."""

import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from app.config import DATABASE_URL

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


async def get_patient_info(patient_id: str) -> Optional[dict]:
    """Fetch patient name and phone number."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, first_name, last_name, emergency_contact
        FROM patients WHERE id = $1
        """,
        uuid.UUID(patient_id),
    )
    if not row:
        return None

    # Try to get patient phone from emergency_contact JSON or a dedicated field
    emergency = row["emergency_contact"] or {}
    return {
        "patient_id": str(row["id"]),
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "full_name": f"{row['first_name']} {row['last_name']}",
        "phone": emergency.get("patient_phone"),  # patient's own phone
        "emergency_contact_phone": emergency.get("phone"),
    }


async def get_alert_by_id(alert_id: str) -> Optional[dict]:
    """Fetch an alert record."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM alerts WHERE id = $1",
        uuid.UUID(alert_id),
    )
    if not row:
        return None
    return dict(row)


async def get_latest_alert_for_patient(patient_id: str) -> Optional[dict]:
    """Fetch the most recent active alert for a patient."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT * FROM alerts
        WHERE patient_id = $1 AND status = 'active'
        ORDER BY triggered_at DESC
        LIMIT 1
        """,
        uuid.UUID(patient_id),
    )
    if not row:
        return None
    return dict(row)


async def store_patient_response(
    patient_id: str,
    alert_id: str,
    response_text: str,
    sentiment: str,
    feels_worse: bool,
) -> str:
    """Store a patient's response to an alert. Returns the response record ID."""
    pool = await get_pool()
    record_id = uuid.uuid4()

    await pool.execute(
        """
        INSERT INTO patient_responses (id, patient_id, alert_id, response_text, sentiment, feels_worse, responded_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        record_id,
        uuid.UUID(patient_id),
        uuid.UUID(alert_id),
        response_text,
        sentiment,
        feels_worse,
        datetime.now(timezone.utc),
    )

    return str(record_id)


async def log_patient_notification(
    patient_id: str,
    alert_id: str,
    channel: str,
    recipient: str,
    message: str,
    status: str,
    error: Optional[str] = None,
) -> str:
    """Log a patient notification dispatch."""
    pool = await get_pool()
    dispatch_id = uuid.uuid4()

    await pool.execute(
        """
        INSERT INTO alert_dispatches (id, alert_id, patient_id, channel, recipient, status, message_preview)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        dispatch_id,
        uuid.UUID(alert_id),
        uuid.UUID(patient_id),
        channel,
        recipient,
        status,
        message[:500],
    )

    return str(dispatch_id)
