"""
ThermalAgent — Monitors body temperature.

Flags:
- Fever: temperature > 38.5°C
- High fever: temperature > 39.5°C
- Hypothermia: temperature < 35.0°C
- Severe hypothermia: temperature < 33.0°C
"""

from typing import Optional

from agents.base_agent import BaseMonitoringAgent
from agents.config import THERMAL_THRESHOLDS
from agents.models import RiskAssessment, Severity, VitalsReading


class ThermalAgent(BaseMonitoringAgent):
    def __init__(self):
        super().__init__(name="ThermalAgent")
        self.thresholds = THERMAL_THRESHOLDS

    async def evaluate(self, reading: VitalsReading) -> Optional[RiskAssessment]:
        temp = reading.temperature
        snapshot = {"temperature": temp}

        # Critical: Severe hypothermia
        if temp < self.thresholds["severe_hypothermia_temp"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.CRITICAL,
                reason=f"Severe hypothermia: {temp}°C — risk of cardiac arrhythmia",
                recommended_action="Active rewarming protocol. Warm IV fluids. Continuous cardiac monitoring. Avoid rough handling.",
                vitals_snapshot=snapshot,
            )

        # High: Hypothermia
        if temp < self.thresholds["hypothermia_temp"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.HIGH,
                reason=f"Hypothermia detected: {temp}°C",
                recommended_action="Passive rewarming (warm blankets). Check for environmental exposure. Monitor core temperature.",
                vitals_snapshot=snapshot,
            )

        # High: High fever
        if temp > self.thresholds["high_fever_temp"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.HIGH,
                reason=f"High fever: {temp}°C",
                recommended_action="Blood cultures x2. Broad-spectrum antibiotics if sepsis suspected. Antipyretics. Cooling measures.",
                vitals_snapshot=snapshot,
            )

        # Medium: Fever
        if temp > self.thresholds["fever_temp"]:
            return self._make_assessment(
                patient_id=reading.patient_id,
                severity=Severity.MEDIUM,
                reason=f"Fever detected: {temp}°C",
                recommended_action="Assess for infection source. Consider antipyretics. Monitor for trend escalation.",
                vitals_snapshot=snapshot,
            )

        return None
