"""
OrchestratorAgent — Collects, merges, and synthesizes specialist agent signals.

Responsibilities:
1. Subscribe to internal Redis channel "agent_signals:{patient_id}"
2. Collect signals within a time window (default 5s)
3. De-duplicate by agent name (keep highest severity per agent)
4. Call Claude to produce a unified clinical summary
5. Compute confidence score based on agent agreement
6. Store the unified alert in PostgreSQL
"""

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import redis.asyncio as redis
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agents.config import (
    ANTHROPIC_API_KEY,
    AUTONOMOUS_ACTIONS_ENABLED,
    DATABASE_URL,
    LLM_MODEL,
    ORCHESTRATOR_DEDUP_SEC,
    ORCHESTRATOR_WINDOW_SEC,
    REDIS_URL,
)
from agents.models import (
    RiskAssessment,
    Severity,
    SEVERITY_ORDER,
    UnifiedAlert,
)
from agents.tools.autonomous_executor import AutonomousExecutor


SYSTEM_PROMPT = """You are a clinical decision support AI. Given multiple agent risk assessments for a patient, determine the overall severity (low/medium/high/critical), write a plain-English summary for the on-call doctor, and suggest one immediate action.

Rules:
- Be concise but clinically precise.
- The summary should be 1-3 sentences a doctor can read in under 10 seconds.
- The action should be a single, specific next step.
- If agents disagree on severity, weigh critical/high signals more heavily.
- Consider whether multiple moderate signals together indicate a more serious situation.

Respond ONLY with valid JSON in this exact format:
{
  "overall_severity": "low|medium|high|critical",
  "summary": "...",
  "action": "..."
}"""


class OrchestratorAgent:
    """
    Collects risk assessments from specialist agents, merges them,
    calls an LLM for synthesis, and persists unified alerts.
    """

    def __init__(self):
        self.name = "OrchestratorAgent"
        self._redis: Optional[redis.Redis] = None
        self._db_pool: Optional[asyncpg.Pool] = None
        self._running = False
        self._llm = ChatAnthropic(
            model=LLM_MODEL,
            api_key=ANTHROPIC_API_KEY,
            max_tokens=500,
            temperature=0,
        )
        # Autonomous action executor
        self._executor = AutonomousExecutor()
        # Pending signals per patient: patient_id -> list of assessments
        self._signal_buffer: dict[str, list[RiskAssessment]] = defaultdict(list)
        # Track last alert time per patient to suppress duplicates
        self._last_alert_time: dict[str, datetime] = {}
        # Pending flush tasks per patient
        self._flush_tasks: dict[str, asyncio.Task] = {}

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    async def _get_db(self) -> asyncpg.Pool:
        if self._db_pool is None:
            self._db_pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=2,
                max_size=10,
            )
        return self._db_pool

    async def start(self, patient_ids: list[str] | None = None):
        """Subscribe to agent signal channels and begin orchestration."""
        r = await self._get_redis()
        pubsub = r.pubsub()

        if patient_ids:
            channels = [f"agent_signals:{pid}" for pid in patient_ids]
            await pubsub.subscribe(*channels)
            print(f"[{self.name}] Listening for signals from {len(channels)} patients")
        else:
            await pubsub.psubscribe("agent_signals:*")
            print(f"[{self.name}] Listening for signals from ALL patients")

        self._running = True
        print(f"[{self.name}] Orchestration active (window={ORCHESTRATOR_WINDOW_SEC}s, dedup={ORCHESTRATOR_DEDUP_SEC}s)")

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break

                if message["type"] not in ("message", "pmessage"):
                    continue

                try:
                    data = json.loads(message["data"])
                    assessment = RiskAssessment(**data)
                    await self._handle_signal(assessment)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[{self.name}] Invalid signal: {e}")

        except asyncio.CancelledError:
            print(f"[{self.name}] Shutting down...")
        finally:
            await pubsub.unsubscribe()
            await pubsub.punsubscribe()
            # Cancel pending flush tasks
            for task in self._flush_tasks.values():
                task.cancel()
            if self._redis:
                await self._redis.aclose()
            if self._db_pool:
                await self._db_pool.close()
            await self._executor.close()

    def stop(self):
        self._running = False

    async def _handle_signal(self, assessment: RiskAssessment):
        """Buffer an incoming signal and schedule a flush after the collection window."""
        patient_id = assessment.patient_id
        self._signal_buffer[patient_id].append(assessment)

        # If no flush is scheduled for this patient, schedule one
        if patient_id not in self._flush_tasks or self._flush_tasks[patient_id].done():
            self._flush_tasks[patient_id] = asyncio.create_task(
                self._delayed_flush(patient_id)
            )

    async def _delayed_flush(self, patient_id: str):
        """Wait for the collection window, then process all buffered signals."""
        await asyncio.sleep(ORCHESTRATOR_WINDOW_SEC)
        signals = self._signal_buffer.pop(patient_id, [])
        if signals:
            await self._process_signals(patient_id, signals)

    async def _process_signals(self, patient_id: str, signals: list[RiskAssessment]):
        """Merge, deduplicate, call LLM, compute confidence, and persist."""
        # De-duplicate: keep highest severity per agent
        deduped = self._deduplicate(signals)

        if not deduped:
            return

        # Check dedup window (suppress if we just alerted for this patient)
        now = datetime.now(timezone.utc)
        last_alert = self._last_alert_time.get(patient_id)
        if last_alert and (now - last_alert).total_seconds() < ORCHESTRATOR_DEDUP_SEC:
            # Check if new signals are higher severity than last
            max_new = max(deduped, key=lambda a: SEVERITY_ORDER[a.severity])
            if SEVERITY_ORDER[max_new.severity] <= SEVERITY_ORDER.get(
                self._last_alert_severity.get(patient_id, Severity.NORMAL), 0
            ):
                return  # Suppress duplicate

        # Call LLM for unified assessment
        unified = await self._call_llm(patient_id, deduped)
        if unified is None:
            return

        # Compute confidence score
        unified.confidence = self._compute_confidence(deduped, unified.overall_severity)

        # Store in PostgreSQL
        await self._persist_alert(unified)

        # Push to dispatch queue for AlertDispatcher
        await self._enqueue_for_dispatch(unified)

        # Execute autonomous actions based on severity
        await self._executor.execute_for_alert(unified)

        # Update dedup tracking
        self._last_alert_time[patient_id] = now
        if not hasattr(self, "_last_alert_severity"):
            self._last_alert_severity: dict[str, Severity] = {}
        self._last_alert_severity[patient_id] = unified.overall_severity

        # Emit to console
        self._emit_unified_alert(unified)

    def _deduplicate(self, signals: list[RiskAssessment]) -> list[RiskAssessment]:
        """Keep only the highest-severity signal per agent."""
        best_per_agent: dict[str, RiskAssessment] = {}
        for signal in signals:
            existing = best_per_agent.get(signal.agent)
            if existing is None or SEVERITY_ORDER[signal.severity] > SEVERITY_ORDER[existing.severity]:
                best_per_agent[signal.agent] = signal
        return list(best_per_agent.values())

    def _compute_confidence(self, signals: list[RiskAssessment], overall_severity: Severity) -> float:
        """
        Confidence score (0-1) based on agent agreement.

        - 1.0 = all agents agree on the same severity
        - Higher when more agents report alerts
        - Lower when agents disagree significantly
        """
        if not signals:
            return 0.0

        total_agents = 4  # total specialist agents in the system
        reporting_agents = len(signals)

        # Factor 1: What fraction of agents reported an alert (0-1)
        coverage = reporting_agents / total_agents

        # Factor 2: How much do agents agree on severity?
        severity_values = [SEVERITY_ORDER[s.severity] for s in signals]
        overall_value = SEVERITY_ORDER[overall_severity]

        if len(severity_values) == 1:
            agreement = 0.7  # single agent, moderate confidence
        else:
            # Calculate how close each agent's severity is to the overall
            max_distance = 4  # max possible distance in severity scale
            distances = [abs(v - overall_value) / max_distance for v in severity_values]
            agreement = 1.0 - (sum(distances) / len(distances))

        # Weighted combination
        confidence = (0.4 * coverage) + (0.6 * agreement)
        return round(min(1.0, max(0.0, confidence)), 2)

    async def _call_llm(self, patient_id: str, signals: list[RiskAssessment]) -> Optional[UnifiedAlert]:
        """Call Claude to synthesize agent signals into a unified alert."""
        # Build the human message with all agent signals
        signals_text = "\n\n".join(
            f"**{s.agent}** (Severity: {s.severity.value.upper()})\n"
            f"  Reason: {s.reason}\n"
            f"  Recommended: {s.recommended_action}\n"
            f"  Vitals: {json.dumps(s.vitals_snapshot) if s.vitals_snapshot else 'N/A'}"
            for s in signals
        )

        human_msg = (
            f"Patient ID: {patient_id}\n"
            f"Number of alerting agents: {len(signals)} / 4\n"
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n\n"
            f"Agent Risk Assessments:\n{signals_text}"
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=human_msg),
            ])

            # Parse LLM response
            response_text = response.content
            if isinstance(response_text, list):
                response_text = response_text[0].get("text", "") if response_text else ""

            # Extract JSON from response
            parsed = self._parse_llm_response(response_text)
            if parsed is None:
                return None

            return UnifiedAlert(
                patient_id=patient_id,
                overall_severity=Severity(parsed["overall_severity"]),
                summary=parsed["summary"],
                action=parsed["action"],
                confidence=0.0,  # will be set by caller
                agent_signals=signals,
                timestamp=datetime.now(timezone.utc),
                llm_model=LLM_MODEL,
            )

        except Exception as e:
            print(f"[{self.name}] LLM call failed: {e}")
            # Fallback: use highest severity from agents without LLM
            return self._fallback_synthesis(patient_id, signals)

    def _parse_llm_response(self, text: str) -> Optional[dict]:
        """Parse JSON from LLM response, handling potential markdown fences."""
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            parsed = json.loads(text)
            if all(k in parsed for k in ("overall_severity", "summary", "action")):
                return parsed
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            import re
            match = re.search(r'\{[^{}]*"overall_severity"[^{}]*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        print(f"[{self.name}] Failed to parse LLM response: {text[:200]}")
        return None

    def _fallback_synthesis(self, patient_id: str, signals: list[RiskAssessment]) -> UnifiedAlert:
        """Fallback when LLM is unavailable — use rule-based synthesis."""
        # Take highest severity
        highest = max(signals, key=lambda s: SEVERITY_ORDER[s.severity])
        reasons = "; ".join(s.reason for s in signals)
        action = highest.recommended_action

        return UnifiedAlert(
            patient_id=patient_id,
            overall_severity=highest.severity,
            summary=f"Multiple agents flagged concerns: {reasons}",
            action=action,
            confidence=0.0,
            agent_signals=signals,
            timestamp=datetime.now(timezone.utc),
            llm_model="fallback_rule_based",
        )

    async def _persist_alert(self, alert: UnifiedAlert):
        """Store the unified alert in the PostgreSQL alerts table."""
        try:
            pool = await self._get_db()
            alert_id = uuid.uuid4()

            # Build vital snapshot from agent signals
            vital_snapshot = {}
            for signal in alert.agent_signals:
                if signal.vitals_snapshot:
                    vital_snapshot.update(signal.vitals_snapshot)

            await pool.execute(
                """
                INSERT INTO alerts (id, patient_id, severity, status, title, description, vital_snapshot, triggered_at)
                VALUES ($1, $2, $3, 'active', $4, $5, $6, $7)
                """,
                alert_id,
                uuid.UUID(alert.patient_id),
                alert.overall_severity.value,
                f"[{alert.overall_severity.value.upper()}] {alert.action[:200]}",
                json.dumps({
                    "summary": alert.summary,
                    "action": alert.action,
                    "confidence": alert.confidence,
                    "agent_signals": [s.model_dump(mode="json") for s in alert.agent_signals],
                    "llm_model": alert.llm_model,
                }),
                json.dumps(vital_snapshot),
                alert.timestamp,
            )

        except Exception as e:
            print(f"[{self.name}] Failed to persist alert: {e}")

    async def _enqueue_for_dispatch(self, alert: UnifiedAlert):
        """Push the unified alert to the Redis dispatch queue for AlertDispatcher."""
        try:
            r = await self._get_redis()
            await r.rpush(
                "queue:alert_dispatch",
                alert.model_dump_json(),
            )
        except Exception as e:
            print(f"[{self.name}] Failed to enqueue for dispatch: {e}")

    def _emit_unified_alert(self, alert: UnifiedAlert):
        """Print the unified alert to console."""
        severity_icons = {
            Severity.LOW: "🟡",
            Severity.MEDIUM: "🟠",
            Severity.HIGH: "🔴",
            Severity.CRITICAL: "🚨",
        }
        icon = severity_icons.get(alert.overall_severity, "ℹ️")
        agents_list = ", ".join(s.agent for s in alert.agent_signals)

        print(
            f"\n{'='*60}\n"
            f"{icon} [{self.name}] UNIFIED ALERT — Patient {alert.patient_id[:8]}...\n"
            f"{'='*60}\n"
            f"   Severity:   {alert.overall_severity.value.upper()}\n"
            f"   Confidence: {alert.confidence:.0%}\n"
            f"   Agents:     {agents_list}\n"
            f"   Summary:    {alert.summary}\n"
            f"   Action:     {alert.action}\n"
            f"   Model:      {alert.llm_model}\n"
            f"{'='*60}\n"
        )
        print(f"   Full JSON: {alert.model_dump_json()}\n")
