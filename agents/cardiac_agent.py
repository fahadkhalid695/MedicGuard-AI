"""
CardiacAgent — Monitors heart rate and blood pressure.

Flags:
- Tachycardia: HR > 100 bpm
- Bradycardia: HR < 50 bpm
- Hypertensive crisis: systolic > 180 mmHg or diastolic > 120 mmHg
- Hypotension: systolic < 90 mmHg
"""

from typing import Optional

from agents.base_agent import BaseMonitoringAgent
from agents.config import CARDIAC_THRESHOLDS
from agents.models import RiskAssessment, Severity, VitalsReading


class CardiacAgent(BaseMonitoringAgent):
    def __init__(self):
        super().__init__(name="CardiacAgent")
        self.thresholds = CARDIAC_THRESHOLDS

    async def evaluate(self, reading: VitalsReading) -> Optional[RiskAssessment]:
        hr = reading.heart_rate
        sys_bp = reading.bp_systolic
        dia_bp = reading.bp_diastolic
        snapshot = {"heart_rate": hr, "bp_systolic": sys_bp, "bp_diastolic": dia_bp}

        # Critical: Hypertensive crisis
        if sys_bp > self.thresholds["hypertensive_systolic"] or dia_bp > self.thresholds["hypertensive_diastolic"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.CRITICAL,
                reason=f"Hypertensive crisis detected: BP {sys_bp}/{dia_bp} mmHg",
                recommended_action="Immediate physician notification. Administer antihypertensive per protocol. Continuous BP monitoring.",
                vitals_snapshot=snapshot,
            )

        # High: Severe tachycardia
        if hr > 150:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.HIGH,
                reason=f"Severe tachycardia: {hr} bpm",
                recommended_action="12-lead ECG stat. Assess for hemodynamic instability. Consider IV beta-blocker if stable.",
                vitals_snapshot=snapshot,
            )

        # Medium: Tachycardia
        if hr > self.thresholds["tachycardia_bpm"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.MEDIUM,
                reason=f"Tachycardia detected: {hr} bpm",
                recommended_action="Assess for pain, anxiety, fever, or dehydration. Monitor trend over next 5 minutes.",
                vitals_snapshot=snapshot,
            )

        # High: Severe bradycardia
        if hr < 35:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.CRITICAL,
                reason=f"Severe bradycardia: {hr} bpm — risk of cardiac arrest",
                recommended_action="Immediate bedside assessment. Prepare atropine. Consider transcutaneous pacing.",
                vitals_snapshot=snapshot,
            )

        # Medium: Bradycardia
        if hr < self.thresholds["bradycardia_bpm"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.MEDIUM,
                reason=f"Bradycardia detected: {hr} bpm",
                recommended_action="Check medication list (beta-blockers, digoxin). Assess for symptoms (dizziness, syncope).",
                vitals_snapshot=snapshot,
            )

        # Medium: Hypotension
        if sys_bp < self.thresholds["hypotensive_systolic"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.MEDIUM,
                reason=f"Hypotension detected: systolic {sys_bp} mmHg",
                recommended_action="Assess volume status. Consider fluid bolus. Check for bleeding or sepsis.",
                vitals_snapshot=snapshot,
            )

        return None
