"""Patient notification channel — calls the patient-facing API."""

import httpx

# The patient-api service URL
PATIENT_API_URL = "http://localhost:8001/api/patient-alert"


async def send_patient_notification(
    patient_id: str,
    alert_id: str,
    severity: str,
    summary: str,
    action: str,
) -> dict:
    """
    Call the patient-facing API to send a simplified alert to the patient.

    Returns: {"patient_message": str, "delivered": bool, "channel": str}
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            PATIENT_API_URL,
            json={
                "patient_id": patient_id,
                "alert_id": alert_id,
                "severity": severity,
                "summary": summary,
                "action": action,
            },
        )

        if response.status_code == 201:
            return response.json()
        elif response.status_code == 422:
            # No phone number — not an error, just can't deliver
            return {"patient_message": "", "delivered": False, "channel": "sms", "reason": "no_phone"}
        else:
            response.raise_for_status()
            return {}
