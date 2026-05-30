"""
TrendAgent — Analyses the last N readings for deterioration trends.

Detects gradual worsening even when individual values remain within normal ranges.
Uses linear regression slope over the sliding window to identify:
- Steadily rising heart rate
- Steadily dropping SpO2
- Steadily rising temperature
- Steadily rising blood pressure
"""

from typing import Optional

from agents.base_agent import BaseMonitoringAgent
from agents.config import TREND_THRESHOLDS
from agents.models import RiskAssessment, Severity, VitalsReading


def compute_slope(values: list[float]) -> float:
    """Simple linear regression slope (least squares) over index-based x."""
    n = len(values)
    if n < 3:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


class TrendAgent(BaseMonitoringAgent):
    def __init__(self):
        super().__init__(
            name="TrendAgent",
            window_size=TREND_THRESHOLDS["window_size"],
        )
        self.thresholds = TREND_THRESHOLDS

    async def evaluate(self, reading: VitalsReading) -> Optional[RiskAssessment]:
        history = self.history[reading.patient_id]

        # Need at least 5 readings to detect a meaningful trend
        if len(history) < 5:
            return None

        readings = list(history)
        alerts: list[str] = []
        max_severity = Severity.NORMAL

        # Heart rate trend (rising = deterioration)
        hr_values = [float(r.heart_rate) for r in readings]
        hr_slope = compute_slope(hr_values)
        if hr_slope > self.thresholds["hr_rise_per_reading"]:
            alerts.append(f"HR trending up: +{hr_slope:.1f} bpm/reading (last {len(readings)} readings)")
            max_severity = max(max_severity, Severity.MEDIUM, key=lambda s: list(Severity).index(s))

        # SpO2 trend (dropping = deterioration)
        spo2_values = [r.spo2 for r in readings]
        spo2_slope = compute_slope(spo2_values)
        if spo2_slope < -self.thresholds["spo2_drop_per_reading"]:
            alerts.append(f"SpO2 trending down: {spo2_slope:.2f}%/reading")
            # SpO2 deterioration is more serious
            max_severity = max(max_severity, Severity.HIGH, key=lambda s: list(Severity).index(s))

        # Temperature trend (rising = potential infection)
        temp_values = [r.temperature for r in readings]
        temp_slope = compute_slope(temp_values)
        if temp_slope > self.thresholds["temp_rise_per_reading"]:
            alerts.append(f"Temperature trending up: +{temp_slope:.2f}°C/reading")
            max_severity = max(max_severity, Severity.MEDIUM, key=lambda s: list(Severity).index(s))

        # Systolic BP trend (rising = worsening hypertension)
        bp_values = [float(r.bp_systolic) for r in readings]
        bp_slope = compute_slope(bp_values)
        if bp_slope > self.thresholds["bp_rise_per_reading"]:
            alerts.append(f"Systolic BP trending up: +{bp_slope:.1f} mmHg/reading")
            max_severity = max(max_severity, Severity.MEDIUM, key=lambda s: list(Severity).index(s))

        # Combined deterioration (multiple trends worsening simultaneously)
        if len(alerts) >= 3:
            max_severity = Severity.HIGH

        if not alerts:
            return None

        # Build snapshot with current values and slopes
        snapshot = {
            "heart_rate": reading.heart_rate,
            "hr_slope": round(hr_slope, 2),
            "spo2": reading.spo2,
            "spo2_slope": round(spo2_slope, 3),
            "temperature": reading.temperature,
            "temp_slope": round(temp_slope, 3),
            "bp_systolic": reading.bp_systolic,
            "bp_slope": round(bp_slope, 2),
            "window_size": len(readings),
        }

        reason = "Deterioration trend detected: " + "; ".join(alerts)

        if max_severity == Severity.HIGH:
            action = "Escalate to attending physician. Patient showing multi-system deterioration despite individual values in range. Consider early intervention."
        else:
            action = "Increase monitoring frequency. Review recent interventions. Reassess in 10 minutes."

        return self._make_assessment(
            patient_id=reading.patient_id,
            severity=max_severity,
            reason=reason,
            recommended_action=action,
            vitals_snapshot=snapshot,
        )
