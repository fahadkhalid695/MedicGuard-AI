"""SMS delivery for patient notifications via Twilio."""

import asyncio
from functools import partial

from twilio.rest import Client

from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER


def _get_client() -> Client:
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not configured")
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


async def send_patient_sms(to_number: str, message: str) -> dict:
    """
    Send an SMS to a patient. Runs Twilio's sync client in a thread pool.

    Returns: {"sid": str, "status": str}
    """
    if not to_number:
        raise ValueError("No patient phone number provided")

    loop = asyncio.get_running_loop()
    client = _get_client()

    result = await loop.run_in_executor(
        None,
        partial(
            client.messages.create,
            body=message,
            from_=TWILIO_FROM_NUMBER,
            to=to_number,
        ),
    )

    return {"sid": result.sid, "status": result.status}
