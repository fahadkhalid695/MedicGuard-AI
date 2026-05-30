"""
RespiratoryAgent — Monitors SpO2 and respiratory rate.

Flags:
- Hypoxia: SpO2 < 92%
- Critical hypoxia: SpO2 < 88%
- Tachypnea: respiratory rate > 25 breaths/min
- Bradypnea: respiratory rate < 8 breaths/min
"""

from typing import Optional

from agents.base_agent import BaseMonitoringAgent
from agents.config import RESPIRATORY_THRESHOLDS
from agents.models import RiskAssessment, Severity, VitalsReading


class RespiratoryAgent(BaseMonitoringAgent):
    def __init__(self):
        super().__init__(name="RespiratoryAgent")
        self.thresholds = RESPIRATORY_THRESHOLDS

    async def evaluate(self, reading: VitalsReading) -> Optional[RiskAssessment]:
        spo2 = reading.spo2
        rr = reading.respiratory_rate
        snapshot = {"spo2": spo2, "respiratory_rate": rr}

        # Critical: Severe hypoxia
        if spo2 < self.thresholds["critical_spo2"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.CRITICAL,
                reason=f"Critical hypoxia: SpO2 at {spo2}%",
                recommended_action="Immediate high-flow oxygen. Assess airway. Prepare for possible intubation. ABG stat.",
                vitals_snapshot=snapshot,
            )

        # High: Hypoxia
        if spo2 < self.thresholds["hypoxia_spo2"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.HIGH,
                reason=f"Hypoxia detected: SpO2 at {spo2}%",
                recommended_action="Increase supplemental oxygen. Assess respiratory effort. Chest auscultation. Consider CXR.",
                vitals_snapshot=snapshot,
            )

        # Respiratory rate checks (only if provided)
        if rr is not None:
            # Critical: Very rapid breathing
            if rr > 35:
                return self._make_assessment(
                    patient_id=reading.patient_id,
                    severity=Severity.HIGH,
                    reason=f"Severe tachypnea: {rr} breaths/min",
                    recommended_action="Assess for respiratory distress. ABG. Consider BiPAP or mechanical ventilation.",
                    vitals_snapshot=snapshot,
                )

            # Medium: Tachypnea
            if rr > self.thresholds["tachypnea_rate"]:
                return self._make_assessment(
                    patient_id=reading.patient_id,
                    severity=Severity.MEDIUM,
                    reason=f"Tachypnea detected: {rr} breaths/min",
                    recommended_action="Assess for pain, anxiety, metabolic acidosis. Monitor SpO2 trend.",
                    vitals_snapshot=snapshot,
                )

            # High: Bradypnea
            if rr < self.thresholds["bradypnea_rate"]:
                return self._make_assessment(
                    patient_id=reading.patient_id,
                    severity=Severity.HIGH,
                    reason=f"Bradypnea detected: {rr} breaths/min",
                    recommended_action="Assess level of consciousness. Check for opioid overdose (consider naloxone). Prepare airway support.",
                    vitals_snapshot=snapshot,
                )

        return None
