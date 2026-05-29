import { v4 as uuidv4 } from "uuid";
import pool from "../db.js";
import type { AlertOutcome, OutcomeRecord } from "../types.js";

/**
 * Record the outcome of an alert after clinical review.
 * Called by doctors/caregivers via the review UI or API.
 */
export async function recordAlertOutcome(params: {
  alert_id: string;
  patient_id: string;
  outcome: AlertOutcome;
  agent_id: string;
  condition_type?: string;
  notes?: string;
  reviewed_by?: string;
  vitals_at_alert?: Record<string, number>;
  vitals_at_review?: Record<string, number>;
}): Promise<OutcomeRecord> {
  const id = uuidv4();
  const now = new Date().toISOString();

  // Calculate time to review from alert trigger time
  const alertResult = await pool.query(
    "SELECT triggered_at FROM alerts WHERE id = $1",
    [params.alert_id]
  );

  let timeToReview: number | null = null;
  if (alertResult.rows[0]) {
    const triggeredAt = new Date(alertResult.rows[0].triggered_at);
    timeToReview = (Date.now() - triggeredAt.getTime()) / 60000; // minutes
  }

  const result = await pool.query(
    `INSERT INTO alert_outcomes (
      id, alert_id, patient_id, outcome, agent_id, condition_type,
      notes, reviewed_by, reviewed_at, vitals_at_alert, vitals_at_review,
      time_to_review_min
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
    RETURNING *`,
    [
      id,
      params.alert_id,
      params.patient_id,
      params.outcome,
      params.agent_id,
      params.condition_type || null,
      params.notes || null,
      params.reviewed_by || null,
      now,
      params.vitals_at_alert ? JSON.stringify(params.vitals_at_alert) : null,
      params.vitals_at_review ? JSON.stringify(params.vitals_at_review) : null,
      timeToReview,
    ]
  );

  // Also update the alert status based on outcome
  const statusMap: Record<string, string> = {
    true_positive: "resolved",
    false_positive: "dismissed",
    doctor_override: "dismissed",
    resolved_naturally: "resolved",
    patient_worsened: "resolved",
  };

  const newStatus = statusMap[params.outcome];
  if (newStatus) {
    await pool.query(
      `UPDATE alerts SET status = $1, resolved_at = NOW(), resolved_by = $2 WHERE id = $3`,
      [newStatus, params.reviewed_by || null, params.alert_id]
    );
  }

  return result.rows[0];
}

/**
 * Get outcomes for a specific alert
 */
export async function getOutcomesByAlert(alertId: string): Promise<OutcomeRecord[]> {
  const result = await pool.query(
    "SELECT * FROM alert_outcomes WHERE alert_id = $1 ORDER BY created_at DESC",
    [alertId]
  );
  return result.rows;
}

/**
 * Get recent outcomes for an agent (for performance calculation)
 */
export async function getOutcomesByAgent(
  agentId: string,
  startDate: Date,
  endDate: Date
): Promise<OutcomeRecord[]> {
  const result = await pool.query(
    `SELECT * FROM alert_outcomes
     WHERE agent_id = $1 AND created_at >= $2 AND created_at < $3
     ORDER BY created_at DESC`,
    [agentId, startDate.toISOString(), endDate.toISOString()]
  );
  return result.rows;
}
