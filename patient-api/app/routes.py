"""
Patient-facing alert and response endpoints.

POST /patient-alert   — Send simplified alert to patient (HIGH/CRITICAL only)
POST /patient-response — Patient replies to an alert
"""

import json
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, status

from app.config import REDIS_URL
from app.db import (
    get_latest_alert_for_patient,
    get_patient_info,
    log_patient_notification,
    store_patient_response,
)
from app.llm import analyze_patient_response, generate_patient_message
from app.models import (
    PatientAlertRequest,
    PatientAlertResponse,
    PatientResponseRequest,
    PatientResponseResult,
    Severity,
)
from app.sms import send_patient_sms

router = APIRouter()

_redis_client: redis.Redis | None = None


async def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


@router.post(
    "/patient-alert",
    response_model=PatientAlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send patient-facing alert notification",
)
async def send_patient_alert(request: PatientAlertRequest) -> PatientAlertResponse:
    """
    For HIGH or CRITICAL alerts, generates a patient-friendly message using Claude
    and sends it via SMS. The message is written in simple, non-medical language.

    Only HIGH and CRITICAL alerts trigger patient notifications.
    """
    # Validate severity — only HIGH/CRITICAL get patient notifications
    if request.severity not in (Severity.HIGH, Severity.CRITICAL):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient notifications only sent for HIGH or CRITICAL alerts. Got: {request.severity.value}",
        )

    # Fetch patient info
    patient = await get_patient_info(request.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    patient_phone = patient.get("phone")
    if not patient_phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No phone number on file for patient. Cannot send SMS.",
        )

    # Generate patient-friendly message via Claude
    try:
        patient_message = await generate_patient_message(
            clinical_summary=request.summary,
            clinical_action=request.action,
        )
    except Exception as e:
        # Fallback: generic message if LLM fails
        patient_message = (
            "We noticed something unusual in your health readings. "
            "Please rest and avoid physical activity. "
            "Your doctor has been notified and will follow up shortly."
        )
        print(f"[PatientAlert] LLM failed, using fallback: {e}")

    # Send SMS
    delivered = False
    dispatch_id = None
    try:
        result = await send_patient_sms(patient_phone, patient_message)
        delivered = True

        dispatch_id = await log_patient_notification(
            patient_id=request.patient_id,
            alert_id=request.alert_id,
            channel="sms_patient",
            recipient=patient_phone,
            message=patient_message,
            status="sent",
        )
        print(f"[PatientAlert] SMS sent to {patient_phone} [SID: {result['sid'][:12]}...]")

    except Exception as e:
        print(f"[PatientAlert] SMS delivery failed: {e}")
        dispatch_id = await log_patient_notification(
            patient_id=request.patient_id,
            alert_id=request.alert_id,
            channel="sms_patient",
            recipient=patient_phone,
            message=patient_message,
            status="failed",
            error=str(e),
        )

    return PatientAlertResponse(
        patient_id=request.patient_id,
        alert_id=request.alert_id,
        patient_message=patient_message,
        channel="sms",
        delivered=delivered,
        dispatch_id=dispatch_id,
    )


@router.post(
    "/patient-response",
    response_model=PatientResponseResult,
    status_code=status.HTTP_201_CREATED,
    summary="Patient responds to an alert",
)
async def handle_patient_response(request: PatientResponseRequest) -> PatientResponseResult:
    """
    Accepts a patient's reply to an alert notification.

    The response is analyzed for sentiment:
    - If the patient reports feeling worse, the system re-triggers agent analysis
      by publishing a priority signal to the agent pipeline.
    - If the patient reports feeling fine, the response is logged for the care team.
    """
    # Validate patient exists
    patient = await get_patient_info(request.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Analyze the response using Claude
    try:
        analysis = await analyze_patient_response(request.response)
    except Exception as e:
        print(f"[PatientResponse] LLM analysis failed, using fallback: {e}")
        # Fallback keyword analysis
        lower = request.response.lower()
        feels_worse = any(kw in lower for kw in ["worse", "bad", "pain", "hurt", "dizzy", "can't breathe"])
        analysis = {
            "sentiment": "negative" if feels_worse else "neutral",
            "feels_worse": feels_worse,
            "reasoning": "Fallback keyword analysis",
        }

    sentiment = analysis["sentiment"]
    feels_worse = analysis["feels_worse"]

    # Store the response
    response_id = await store_patient_response(
        patient_id=request.patient_id,
        alert_id=request.alert_id,
        response_text=request.response,
        sentiment=sentiment,
        feels_worse=feels_worse,
    )

    # Determine action
    action_taken = "Response logged for care team review."

    if feels_worse:
        # Re-trigger agent analysis by publishing a priority signal
        action_taken = "Patient reports worsening. Priority re-analysis triggered. Care team notified."
        await _trigger_reanalysis(request.patient_id, request.alert_id, request.response)

    return PatientResponseResult(
        response_id=response_id,
        patient_id=request.patient_id,
        alert_id=request.alert_id,
        sentiment=sentiment,
        feels_worse=feels_worse,
        action_taken=action_taken,
        timestamp=datetime.now(timezone.utc),
    )


async def _trigger_reanalysis(patient_id: str, alert_id: str, patient_response: str):
    """
    Publish a priority signal to the agent pipeline when a patient reports feeling worse.
    This triggers immediate re-evaluation of the patient's vitals.
    """
    r = await _get_redis()

    # Publish to a priority channel that the orchestrator monitors
    signal = json.dumps({
        "type": "patient_escalation",
        "patient_id": patient_id,
        "alert_id": alert_id,
        "patient_response": patient_response,
        "reason": "Patient self-reported worsening condition",
        "priority": "high",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Publish to the agent signals channel to trigger orchestrator
    await r.publish(f"agent_signals:{patient_id}", json.dumps({
        "agent": "PatientSelfReport",
        "patient_id": patient_id,
        "severity": "high",
        "reason": f"Patient reports feeling worse: '{patient_response[:100]}'",
        "recommended_action": "Immediate re-evaluation of patient vitals. Contact patient directly.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vitals_snapshot": None,
    }))

    # Also push to a dedicated escalation queue for the care team
    await r.rpush("queue:patient_escalations", signal)

    print(f"[PatientResponse] ⚠ Re-analysis triggered for patient {patient_id[:8]}...")


@router.get(
    "/patient-alert/{patient_id}/latest",
    summary="Get the latest alert message sent to a patient",
)
async def get_latest_patient_alert(patient_id: str):
    """Returns the most recent alert and patient-friendly message for a patient."""
    alert = await get_latest_alert_for_patient(patient_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active alerts for this patient",
        )

    return {
        "patient_id": patient_id,
        "alert_id": str(alert["id"]),
        "severity": alert["severity"],
        "title": alert["title"],
        "triggered_at": alert["triggered_at"].isoformat() if alert["triggered_at"] else None,
        "status": alert["status"],
    }
