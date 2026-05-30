"""
Autonomous Action Executor

Applies severity-based autonomy rules to determine which tools the
OrchestratorAgent can invoke without human approval:

- MEDIUM:   contact_caregiver only
- HIGH:     schedule_consultation + contact_caregiver
- CRITICAL: all four tools simultaneously

Every action is logged to the agent_actions table.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from agents.config import AUTONOMOUS_ACTIONS_ENABLED, DATABASE_URL
from agents.models import Severity, SEVERITY_ORDER, UnifiedAlert
from agents.tools.definitions import (
    contact_caregiver,
    notify_hospital,
    request_patient_checkin,
    schedule_consultation,
)


# Autonomy rules: which tools are allowed at each severity level
AUTONOMY_RULES: dict[Severity, list[str]] = {
    Severity.LOW: [],
    Severity.MEDIUM: ["contact_caregiver"],
    Severity.HIGH: ["schedule_consultation", "contact_caregiver"],
    Severity.CRITICAL: [
        "schedule_consultation",
        "notify_hospital",
        "contact_caregiver",
        "request_patient_checkin",
    ],
}


class AutonomousExecutor:
    """
    Executes autonomous actions based on the unified alert severity.
    Logs every action (success or failure) to the agent_actions table.
    """

    def __init__(self):
        self._db_pool: Optional[asyncpg.Pool] = None

    async def _get_db(self) -> asyncpg.Pool:
        if self._db_pool is None:
            self._db_pool = await asyncpg.create_pool(
                dsn=DATABASE_URL, min_size=2, max_size=5
            )
        return self._db_pool

    async def close(self):
        if self._db_pool:
            await self._db_pool.close()
            self._db_pool = None

    async def execute_for_alert(self, alert: UnifiedAlert) -> list[dict]:
        """
        Determine and execute autonomous actions based on alert severity.

        Returns a list of action results with their outcomes.
        """
        if not AUTONOMOUS_ACTIONS_ENABLED:
            return []

        severity = alert.overall_severity
        allowed_actions = AUTONOMY_RULES.get(severity, [])

        if not allowed_actions:
            return []

        print(
            f"\n⚡ [AutonomousExecutor] Severity={severity.value.upper()} → "
            f"Executing {len(allowed_actions)} autonomous action(s): {', '.join(allowed_actions)}"
        )

        # Build tasks for all allowed actions
        tasks = []
        for action_name in allowed_actions:
            tasks.append(self._execute_action(action_name, alert))

        # Execute all allowed actions concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        action_results = []
        for i, result in enumerate(results):
            action_name = allowed_actions[i]
            if isinstance(result, Exception):
                action_results.append({
                    "action": action_name,
                    "outcome": "failed",
                    "detail": str(result),
                })
            else:
                action_results.append(result)

        return action_results

    async def _execute_action(self, action_name: str, alert: UnifiedAlert) -> dict:
        """Execute a single autonomous action and log it."""
        patient_id = alert.patient_id
        result = {
            "action": action_name,
            "outcome": "pending",
            "detail": "",
        }

        try:
            if action_name == "schedule_consultation":
                urgency = self._determine_urgency(alert.overall_severity)
                tool_result = await schedule_consultation.ainvoke({
                    "patient_id": patient_id,
                    "urgency": urgency,
                })
                result["outcome"] = "success"
                result["detail"] = tool_result
                result["params"] = {"urgency": urgency}

            elif action_name == "notify_hospital":
                tool_result = await notify_hospital.ainvoke({
                    "patient_id": patient_id,
                    "condition_summary": alert.summary,
                })
                result["outcome"] = "success"
                result["detail"] = tool_result
                result["params"] = {"condition_summary": alert.summary}

            elif action_name == "contact_caregiver":
                message = self._build_caregiver_message(alert)
                tool_result = await contact_caregiver.ainvoke({
                    "patient_id": patient_id,
                    "message": message,
                })
                result["outcome"] = "success"
                result["detail"] = tool_result
                result["params"] = {"message": message}

            elif action_name == "request_patient_checkin":
                tool_result = await request_patient_checkin.ainvoke({
                    "patient_id": patient_id,
                })
                result["outcome"] = "success"
                result["detail"] = tool_result
                result["params"] = {}

            else:
                result["outcome"] = "skipped"
                result["detail"] = f"Unknown action: {action_name}"

        except Exception as e:
            result["outcome"] = "failed"
            result["detail"] = str(e)

        # Log to database
        await self._log_action(
            action_type=action_name,
            patient_id=patient_id,
            alert_id=None,  # could be passed if we store alert_id on UnifiedAlert
            triggered_by="OrchestratorAgent",
            severity=alert.overall_severity.value,
            input_params=result.get("params", {}),
            outcome=result["outcome"],
            outcome_detail=result["detail"],
        )

        # Console output
        icon = "✓" if result["outcome"] == "success" else "✗"
        print(f"   {icon} {action_name}: {result['outcome']}")

        return result

    async def _log_action(
        self,
        action_type: str,
        patient_id: str,
        alert_id: Optional[str],
        triggered_by: str,
        severity: str,
        input_params: dict,
        outcome: str,
        outcome_detail: str,
    ) -> None:
        """Log an autonomous action to the agent_actions table."""
        try:
            pool = await self._get_db()
            await pool.execute(
                """
                INSERT INTO agent_actions (id, action_type, patient_id, alert_id, triggered_by, severity, input_params, outcome, outcome_detail, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                uuid.uuid4(),
                action_type,
                uuid.UUID(patient_id),
                uuid.UUID(alert_id) if alert_id else None,
                triggered_by,
                severity,
                json.dumps(input_params),
                outcome,
                outcome_detail[:1000] if outcome_detail else "",
                datetime.now(timezone.utc),
            )
        except Exception as e:
            print(f"   ⚠ Failed to log action to DB: {e}")

    def _determine_urgency(self, severity: Severity) -> str:
        """Map alert severity to consultation urgency."""
        if severity == Severity.CRITICAL:
            return "immediate"
        elif severity == Severity.HIGH:
            return "urgent"
        return "routine"

    def _build_caregiver_message(self, alert: UnifiedAlert) -> str:
        """Build a concise message for the caregiver."""
        severity_label = alert.overall_severity.value.upper()
        return (
            f"MediGuard AI Alert ({severity_label}): "
            f"{alert.summary} "
            f"Action: {alert.action} "
            f"Please check on the patient."
        )
