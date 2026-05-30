"""
AlertDispatcher — Routes unified alerts to appropriate notification channels.

Routing rules by severity:
- LOW:      Log to DB only
- MEDIUM:   In-app WebSocket notification to assigned doctor
- HIGH:     SMS to doctor + in-app notification
- CRITICAL: SMS to doctor + SMS to caregiver + email + POST to hospital endpoint

All dispatches are logged to the alert_dispatches table with delivery status.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis

from dispatcher.channels.email import build_alert_email_html, send_email
from dispatcher.channels.hospital import notify_hospital
from dispatcher.channels.patient_notify import send_patient_notification
from dispatcher.channels.sms import send_sms
from dispatcher.channels.websocket import send_ws_notification
from dispatcher.config import DASHBOARD_BASE_URL, DISPATCH_QUEUE, REDIS_URL
from dispatcher.db import (
    close_pool,
    fetch_patient_context,
    get_pool,
    log_dispatch,
    update_dispatch_status,
)
from dispatcher.models import (
    DeliveryStatus,
    DispatchChannel,
    PatientContext,
    Severity,
    UnifiedAlert,
)


class AlertDispatcher:
    """
    Consumes unified alerts from a Redis queue and dispatches notifications
    based on severity level. Non-blocking — uses async queues so the main
    agent pipeline is never held up.
    """

    def __init__(self):
        self.name = "AlertDispatcher"
        self._redis: Optional[redis.Redis] = None
        self._running = False

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    async def start(self):
        """Start consuming from the dispatch queue."""
        r = await self._get_redis()
        await get_pool()  # warm up DB pool
        self._running = True

        print(f"[{self.name}] Consuming from queue: {DISPATCH_QUEUE}")
        print(f"[{self.name}] Routing rules:")
        print(f"   LOW      → DB log only")
        print(f"   MEDIUM   → WebSocket to doctor")
        print(f"   HIGH     → SMS to doctor + WebSocket")
        print(f"   CRITICAL → SMS (doctor + caregiver) + Email + Hospital POST")
        print(f"[{self.name}] Ready.\n")

        try:
            while self._running:
                # BLPOP blocks until an item is available (timeout 1s for shutdown check)
                result = await r.blpop(DISPATCH_QUEUE, timeout=1)
                if result is None:
                    continue

                _, raw_data = result
                try:
                    alert_data = json.loads(raw_data)
                    alert = UnifiedAlert(**alert_data)
                    await self._dispatch(alert)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[{self.name}] Invalid alert in queue: {e}")

        except asyncio.CancelledError:
            print(f"[{self.name}] Shutting down...")
        finally:
            if self._redis:
                await self._redis.aclose()
            await close_pool()

    def stop(self):
        self._running = False

    async def _dispatch(self, alert: UnifiedAlert):
        """Route the alert based on severity."""
        # Fetch patient context (name, doctor/caregiver contacts)
        context = await fetch_patient_context(alert.patient_id)
        if context is None:
            print(f"[{self.name}] Patient {alert.patient_id[:8]} not found in DB. Logging only.")
            context = PatientContext(
                patient_id=alert.patient_id,
                first_name="Unknown",
                last_name="Patient",
                full_name="Unknown Patient",
            )

        # Generate a pseudo alert_id for dispatch logging
        alert_id = str(uuid.uuid4())
        dashboard_link = f"{DASHBOARD_BASE_URL}/patients/{alert.patient_id}/live"

        severity = alert.overall_severity
        print(
            f"[{self.name}] Dispatching {severity.value.upper()} alert for "
            f"{context.full_name} ({alert.patient_id[:8]}...)"
        )

        # Always log to DB
        await self._log_to_db(alert_id, alert, context)

        # Route based on severity
        if severity == Severity.LOW:
            pass  # DB log only

        elif severity == Severity.MEDIUM:
            await self._send_websocket(alert_id, alert, context, dashboard_link)

        elif severity == Severity.HIGH:
            await asyncio.gather(
                self._send_websocket(alert_id, alert, context, dashboard_link),
                self._send_sms_doctor(alert_id, alert, context, dashboard_link),
                self._send_patient_alert(alert_id, alert),
                return_exceptions=True,
            )

        elif severity == Severity.CRITICAL:
            await asyncio.gather(
                self._send_websocket(alert_id, alert, context, dashboard_link),
                self._send_sms_doctor(alert_id, alert, context, dashboard_link),
                self._send_sms_caregiver(alert_id, alert, context, dashboard_link),
                self._send_email_summary(alert_id, alert, context, dashboard_link),
                self._notify_hospital(alert_id, alert, context),
                self._send_patient_alert(alert_id, alert),
                return_exceptions=True,
            )

    async def _log_to_db(self, alert_id: str, alert: UnifiedAlert, context: PatientContext):
        """Log the alert to the dispatches table (always happens)."""
        try:
            await log_dispatch(
                alert_id=alert_id,
                patient_id=alert.patient_id,
                channel=DispatchChannel.DB_LOG,
                recipient="system",
                status=DeliveryStatus.DELIVERED,
                message_preview=f"[{alert.overall_severity.value.upper()}] {alert.summary[:200]}",
            )
        except Exception as e:
            print(f"[{self.name}] DB log failed: {e}")

    async def _send_websocket(
        self, alert_id: str, alert: UnifiedAlert, context: PatientContext, dashboard_link: str
    ):
        """Send in-app notification via WebSocket."""
        dispatch_id = None
        try:
            dispatch_id = await log_dispatch(
                alert_id=alert_id,
                patient_id=alert.patient_id,
                channel=DispatchChannel.WEBSOCKET,
                recipient=context.doctor_name or "dashboard",
                status=DeliveryStatus.PENDING,
                message_preview=alert.summary[:200],
            )

            payload = {
                "patient_id": alert.patient_id,
                "patient_name": context.full_name,
                "severity": alert.overall_severity.value,
                "summary": alert.summary,
                "action": alert.action,
                "confidence": alert.confidence,
                "dashboard_link": dashboard_link,
                "timestamp": alert.timestamp.isoformat(),
            }

            notified = await send_ws_notification(alert.patient_id, payload)

            status = DeliveryStatus.DELIVERED if notified else DeliveryStatus.SENT
            await update_dispatch_status(dispatch_id, status)
            print(f"   ✓ WebSocket: notified {len(notified)} subscriber(s)")

        except Exception as e:
            print(f"   ✗ WebSocket failed: {e}")
            if dispatch_id:
                await update_dispatch_status(dispatch_id, DeliveryStatus.FAILED, str(e))

    async def _send_sms_doctor(
        self, alert_id: str, alert: UnifiedAlert, context: PatientContext, dashboard_link: str
    ):
        """Send SMS to the assigned doctor."""
        if not context.doctor_phone:
            print(f"   ⚠ SMS (doctor): No phone number on file")
            return

        dispatch_id = None
        try:
            message = (
                f"🚨 MediGuard AI Alert — {alert.overall_severity.value.upper()}\n"
                f"Patient: {context.full_name}\n"
                f"Summary: {alert.summary}\n"
                f"Action: {alert.action}\n"
                f"Dashboard: {dashboard_link}"
            )

            dispatch_id = await log_dispatch(
                alert_id=alert_id,
                patient_id=alert.patient_id,
                channel=DispatchChannel.SMS_DOCTOR,
                recipient=context.doctor_phone,
                status=DeliveryStatus.PENDING,
                message_preview=message[:200],
            )

            result = await send_sms(context.doctor_phone, message)
            await update_dispatch_status(dispatch_id, DeliveryStatus.SENT)
            print(f"   ✓ SMS (doctor): sent to {context.doctor_phone} [SID: {result['sid'][:12]}...]")

        except Exception as e:
            print(f"   ✗ SMS (doctor) failed: {e}")
            if dispatch_id:
                await update_dispatch_status(dispatch_id, DeliveryStatus.FAILED, str(e))

    async def _send_sms_caregiver(
        self, alert_id: str, alert: UnifiedAlert, context: PatientContext, dashboard_link: str
    ):
        """Send SMS to the assigned caregiver (CRITICAL only)."""
        if not context.caregiver_phone:
            print(f"   ⚠ SMS (caregiver): No phone number on file")
            return

        dispatch_id = None
        try:
            message = (
                f"🚨 CRITICAL Alert — {context.full_name}\n"
                f"{alert.summary}\n"
                f"Action needed: {alert.action}\n"
                f"View: {dashboard_link}"
            )

            dispatch_id = await log_dispatch(
                alert_id=alert_id,
                patient_id=alert.patient_id,
                channel=DispatchChannel.SMS_CAREGIVER,
                recipient=context.caregiver_phone,
                status=DeliveryStatus.PENDING,
                message_preview=message[:200],
            )

            result = await send_sms(context.caregiver_phone, message)
            await update_dispatch_status(dispatch_id, DeliveryStatus.SENT)
            print(f"   ✓ SMS (caregiver): sent to {context.caregiver_phone}")

        except Exception as e:
            print(f"   ✗ SMS (caregiver) failed: {e}")
            if dispatch_id:
                await update_dispatch_status(dispatch_id, DeliveryStatus.FAILED, str(e))

    async def _send_email_summary(
        self, alert_id: str, alert: UnifiedAlert, context: PatientContext, dashboard_link: str
    ):
        """Send email summary to the doctor (CRITICAL only)."""
        if not context.doctor_email:
            print(f"   ⚠ Email: No email address on file for doctor")
            return

        dispatch_id = None
        try:
            subject = f"🚨 CRITICAL: {context.full_name} — {alert.action[:80]}"

            html_body = build_alert_email_html(
                patient_name=context.full_name,
                severity=alert.overall_severity.value,
                summary=alert.summary,
                action=alert.action,
                dashboard_link=dashboard_link,
                agent_signals=[s.model_dump(mode="json") for s in alert.agent_signals],
            )

            dispatch_id = await log_dispatch(
                alert_id=alert_id,
                patient_id=alert.patient_id,
                channel=DispatchChannel.EMAIL,
                recipient=context.doctor_email,
                status=DeliveryStatus.PENDING,
                message_preview=f"Subject: {subject}",
            )

            result = await send_email(context.doctor_email, subject, html_body)
            await update_dispatch_status(dispatch_id, DeliveryStatus.SENT)
            print(f"   ✓ Email: sent to {context.doctor_email} [status: {result['status_code']}]")

        except Exception as e:
            print(f"   ✗ Email failed: {e}")
            if dispatch_id:
                await update_dispatch_status(dispatch_id, DeliveryStatus.FAILED, str(e))

    async def _notify_hospital(self, alert_id: str, alert: UnifiedAlert, context: PatientContext):
        """POST to hospital notification endpoint (CRITICAL only)."""
        dispatch_id = None
        try:
            # Build vital snapshot from agent signals
            vitals = {}
            for sig in alert.agent_signals:
                if sig.vitals_snapshot:
                    vitals.update(sig.vitals_snapshot)

            payload = {
                "patient_id": alert.patient_id,
                "patient_name": context.full_name,
                "severity": alert.overall_severity.value,
                "summary": alert.summary,
                "action": alert.action,
                "location": context.location or "Unknown",
                "vitals_snapshot": vitals,
                "confidence": alert.confidence,
                "timestamp": alert.timestamp.isoformat(),
            }

            from dispatcher.config import HOSPITAL_NOTIFY_URL

            dispatch_id = await log_dispatch(
                alert_id=alert_id,
                patient_id=alert.patient_id,
                channel=DispatchChannel.HOSPITAL_NOTIFY,
                recipient=HOSPITAL_NOTIFY_URL,
                status=DeliveryStatus.PENDING,
                message_preview=json.dumps(payload)[:200],
            )

            result = await notify_hospital(payload)
            await update_dispatch_status(dispatch_id, DeliveryStatus.DELIVERED)
            print(f"   ✓ Hospital: notified [status: {result['status_code']}]")

        except Exception as e:
            print(f"   ✗ Hospital notification failed: {e}")
            if dispatch_id:
                await update_dispatch_status(dispatch_id, DeliveryStatus.FAILED, str(e))

    async def _send_patient_alert(self, alert_id: str, alert: UnifiedAlert):
        """Send patient-facing notification via the patient-api service (HIGH/CRITICAL)."""
        try:
            result = await send_patient_notification(
                patient_id=alert.patient_id,
                alert_id=alert_id,
                severity=alert.overall_severity.value,
                summary=alert.summary,
                action=alert.action,
            )

            if result.get("delivered"):
                print(f"   ✓ Patient SMS: delivered")
            else:
                reason = result.get("reason", "unknown")
                print(f"   ⚠ Patient SMS: not delivered ({reason})")

        except Exception as e:
            print(f"   ✗ Patient notification failed: {e}")
