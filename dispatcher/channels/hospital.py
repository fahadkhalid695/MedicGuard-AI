"""Hospital system notification channel via HTTP POST."""

import httpx

from dispatcher.config import HOSPITAL_NOTIFY_URL


async def notify_hospital(payload: dict) -> dict:
    """
    POST alert data to the hospital's notification endpoint.

    Expected payload:
    {
        "patient_id": str,
        "patient_name": str,
        "severity": str,
        "summary": str,
        "action": str,
        "location": str,
        "vitals_snapshot": dict,
        "timestamp": str
    }

    Returns:
        {"status_code": int, "response": str} on success
    Raises:
        Exception on failure
    """
    if not HOSPITAL_NOTIFY_URL:
        raise RuntimeError("Hospital notification URL not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            HOSPITAL_NOTIFY_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Source": "MediGuard-AI",
                "X-Alert-Severity": payload.get("severity", "unknown"),
            },
        )
        response.raise_for_status()

        return {
            "status_code": response.status_code,
            "response": response.text[:500],
        }
