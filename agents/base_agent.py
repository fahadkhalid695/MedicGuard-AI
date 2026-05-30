"""Base class for all monitoring agents."""

import asyncio
import json
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis

from agents.config import REDIS_URL
from agents.models import RiskAssessment, Severity, VitalsReading


class BaseMonitoringAgent(ABC):
    """
    Abstract base for specialist monitoring agents.

    Each agent:
    - Subscribes to Redis Pub/Sub vitals channels
    - Maintains a sliding window of recent readings per patient
    - Evaluates each reading against its domain-specific rules
    - Outputs structured RiskAssessment JSON
    """

    def __init__(self, name: str, window_size: int = 10):
        self.name = name
        self.window_size = window_size
        self._redis: Optional[redis.Redis] = None
        self._running = False
        # Per-patient sliding window of recent readings
        self.history: dict[str, deque[VitalsReading]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    async def start(self, patient_ids: list[str] | None = None):
        """Subscribe to vitals channels and begin monitoring."""
        r = await self._get_redis()
        pubsub = r.pubsub()

        if patient_ids:
            channels = [f"vitals:{pid}" for pid in patient_ids]
            await pubsub.subscribe(*channels)
            print(f"[{self.name}] Subscribed to {len(channels)} patient channels")
        else:
            # Pattern subscribe to all patients
            await pubsub.psubscribe("vitals:*")
            print(f"[{self.name}] Subscribed to vitals:* (all patients)")

        self._running = True
        print(f"[{self.name}] Monitoring active...")

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break

                if message["type"] not in ("message", "pmessage"):
                    continue

                try:
                    data = json.loads(message["data"])
                    reading = VitalsReading(**data)
                    self.history[reading.patient_id].append(reading)

                    assessment = await self.evaluate(reading)
                    if assessment and assessment.is_alert():
                        self._emit_alert(assessment)
                        await self._publish_assessment(assessment)

                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[{self.name}] Invalid message: {e}")

        except asyncio.CancelledError:
            print(f"[{self.name}] Shutting down...")
        finally:
            await pubsub.unsubscribe()
            await pubsub.punsubscribe()
            if self._redis:
                await self._redis.aclose()

    def stop(self):
        """Signal the agent to stop."""
        self._running = False

    @abstractmethod
    async def evaluate(self, reading: VitalsReading) -> Optional[RiskAssessment]:
        """
        Evaluate a vitals reading. Return a RiskAssessment if action is needed,
        or None if everything is normal.
        """
        ...

    def _make_assessment(
        self,
        patient_id: str,
        severity: Severity,
        reason: str,
        recommended_action: str,
        vitals_snapshot: dict | None = None,
    ) -> RiskAssessment:
        return RiskAssessment(
            agent=self.name,
            patient_id=patient_id,
            severity=severity,
            reason=reason,
            recommended_action=recommended_action,
            timestamp=datetime.now(timezone.utc),
            vitals_snapshot=vitals_snapshot,
        )

    def _emit_alert(self, assessment: RiskAssessment):
        """Output the alert. Also publishes to internal channel for orchestrator."""
        severity_icons = {
            Severity.LOW: "🟡",
            Severity.MEDIUM: "🟠",
            Severity.HIGH: "🔴",
            Severity.CRITICAL: "🚨",
        }
        icon = severity_icons.get(assessment.severity, "ℹ️")
        print(
            f"\n{icon} [{self.name}] ALERT — Patient {assessment.patient_id[:8]}...\n"
            f"   Severity: {assessment.severity.value.upper()}\n"
            f"   Reason: {assessment.reason}\n"
            f"   Action: {assessment.recommended_action}\n"
        )

    async def _publish_assessment(self, assessment: RiskAssessment):
        """Publish assessment to internal Redis channel for orchestrator consumption."""
        try:
            r = await self._get_redis()
            channel = f"agent_signals:{assessment.patient_id}"
            await r.publish(channel, assessment.model_dump_json())
        except Exception as e:
            print(f"[{self.name}] Failed to publish assessment: {e}")
