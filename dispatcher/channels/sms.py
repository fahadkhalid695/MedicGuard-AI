"""SMS notification channel via Twilio."""

import asyncio
from functools import partial

from twilio.rest import Client

from dispatcher.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER


def _get_twilio_client() -> Client:
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not configured")
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


async def send_sms(to_number: str, message: str) -> dict:
    """
    Send an SMS via Twilio. Runs the synchronous Twilio client in a thread pool.

    Returns:
        {"sid": str, "status": str} on success
    Raises:
        Exception on failure
    """
    if not to_number:
        raise ValueError("No phone number provided")

    # Truncate to SMS limit (1600 chars for Twilio)
    body = message[:1600]

    loop = asyncio.get_running_loop()
    client = _get_twilio_client()

    # Run blocking Twilio call in executor
    result = await loop.run_in_executor(
        None,
        partial(
            client.messages.create,
            body=body,
            from_=TWILIO_FROM_NUMBER,
            to=to_number,
        ),
    )

    return {
        "sid": result.sid,
        "status": result.status,
    }
