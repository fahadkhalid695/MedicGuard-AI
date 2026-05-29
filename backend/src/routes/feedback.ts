import { Router, Request, Response } from "express";
import { recordAlertOutcome, getOutcomesByAlert } from "../services/outcome-tracking.js";
import {
  createABTest,
  assignPatientsToABTest,
  startABTest,
  completeABTest,
  getABTestResults,
} from "../services/ab-testing.js";
import pool from "../db.js";
import type { AlertOutcome, ABGroup } from "../types.js";

const router = Router();

// ==========================================
// OUTCOME TRACKING
// ==========================================

/** Record an alert outcome */
router.post("/outcomes", async (req: Request, res: Response) => {
  try {
    const { alert_id, patient_id, outcome, agent_id, condition_type, notes, reviewed_by, vitals_at_alert, vitals_at_review } = req.body;

    if (!alert_id || !patient_id || !outcome || !agent_id) {
      res.status(400).json({ error: "Missing required fields: alert_id, patient_id, outcome, agent_id" });
      return;
    }

    const record = await recordAlertOutcome({
      alert_id,
      patient_id,
      outcome: outcome as AlertOutcome,
      agent_id,
      condition_type,
      notes,
      reviewed_by,
      vitals_at_alert,
      vitals_at_review,
    });

    res.status(201).json(record);
  } catch (err) {
    console.error("Error recording outcome:", err);
    res.status(500).json({ error: "Failed to record outcome" });
  }
});

/** Get outcomes for an alert */
router.get("/outcomes/alert/:alertId", async (req: Request, res: Response) => {
  try {
    const outcomes = await getOutcomesByAlert(req.params.alertId);
    res.json(outcomes);
  } catch (err) {
    console.error("Error fetching outcomes:", err);
    res.status(500).json({ error: "Failed to fetch outcomes" });
  }
});

// ==========================================
// PERFORMANCE METRICS
// ==========================================

/** Get performance trends for an agent */
router.get("/performance/:agentId/trends", async (req: Request, res: Response) => {
  try {
    const { agentId } = req.params;
    const { weeks = "12", condition } = req.query;

    const result = await pool.query(
      `SELECT period_start, precision_rate, recall_rate, f1_score,
              false_positive_rate, total_alerts, ab_group, threshold_version
       FROM agent_performance
       WHERE agent_id = $1
         AND condition_type ${condition ? "= $3" : "IS NULL"}
       ORDER BY period_start DESC
       LIMIT $2`,
      condition ? [agentId, parseInt(weeks as string), condition] : [agentId, parseInt(weeks as string)]
    );

    res.json(result.rows.reverse()); // chronological order
  } catch (err) {
    console.error("Error fetching trends:", err);
    res.status(500).json({ error: "Failed to fetch performance trends" });
  }
});

/** Get latest performance summary for all agents */
router.get("/performance/summary", async (_req: Request, res: Response) => {
  try {
    const result = await pool.query(
      `SELECT DISTINCT ON (agent_id)
         agent_id, period_start, period_end,
         precision_rate, recall_rate, f1_score, false_positive_rate,
         total_alerts, true_positives, false_positives, doctor_overrides,
         threshold_version
       FROM agent_performance
       WHERE condition_type IS NULL
       ORDER BY agent_id, period_start DESC`
    );

    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching summary:", err);
    res.status(500).json({ error: "Failed to fetch performance summary" });
  }
});

// ==========================================
// A/B TESTING
// ==========================================

/** Create a new A/B test */
router.post("/ab-tests", async (req: Request, res: Response) => {
  try {
    const test = await createABTest(req.body);
    res.status(201).json(test);
  } catch (err) {
    console.error("Error creating A/B test:", err);
    res.status(500).json({ error: "Failed to create A/B test" });
  }
});

/** Assign patients to A/B test groups */
router.post("/ab-tests/:id/assign", async (req: Request, res: Response) => {
  try {
    const { patient_ids } = req.body;
    const groups = await assignPatientsToABTest(req.params.id, patient_ids);
    res.json(groups);
  } catch (err) {
    console.error("Error assigning patients:", err);
    res.status(500).json({ error: "Failed to assign patients" });
  }
});

/** Start an A/B test */
router.post("/ab-tests/:id/start", async (req: Request, res: Response) => {
  try {
    await startABTest(req.params.id);
    res.json({ status: "running" });
  } catch (err) {
    console.error("Error starting A/B test:", err);
    res.status(500).json({ error: "Failed to start A/B test" });
  }
});

/** Complete an A/B test */
router.post("/ab-tests/:id/complete", async (req: Request, res: Response) => {
  try {
    const { winner } = req.body;
    await completeABTest(req.params.id, winner as ABGroup | undefined);
    res.json({ status: "completed", winner });
  } catch (err) {
    console.error("Error completing A/B test:", err);
    res.status(500).json({ error: "Failed to complete A/B test" });
  }
});

/** Get A/B test results */
router.get("/ab-tests/:id/results", async (req: Request, res: Response) => {
  try {
    const results = await getABTestResults(req.params.id);
    res.json(results);
  } catch (err) {
    console.error("Error fetching A/B results:", err);
    res.status(500).json({ error: "Failed to fetch A/B test results" });
  }
});

// ==========================================
// THRESHOLD CONFIGS
// ==========================================

/** List all threshold configs */
router.get("/thresholds", async (_req: Request, res: Response) => {
  try {
    const result = await pool.query(
      "SELECT * FROM threshold_configs ORDER BY created_at DESC"
    );
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching thresholds:", err);
    res.status(500).json({ error: "Failed to fetch thresholds" });
  }
});

/** Activate a threshold config (promote suggestion) */
router.post("/thresholds/:id/activate", async (req: Request, res: Response) => {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    // Get the config to activate
    const config = await client.query("SELECT * FROM threshold_configs WHERE id = $1", [req.params.id]);
    if (config.rows.length === 0) {
      res.status(404).json({ error: "Threshold config not found" });
      return;
    }

    const agentId = config.rows[0].agent_id;

    // Deactivate current
    await client.query(
      "UPDATE threshold_configs SET is_active = FALSE, deactivated_at = NOW() WHERE agent_id = $1 AND is_active = TRUE",
      [agentId]
    );

    // Activate new
    await client.query(
      "UPDATE threshold_configs SET is_active = TRUE, activated_at = NOW() WHERE id = $1",
      [req.params.id]
    );

    await client.query("COMMIT");
    res.json({ status: "activated" });
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("Error activating threshold:", err);
    res.status(500).json({ error: "Failed to activate threshold" });
  } finally {
    client.release();
  }
});

// ==========================================
// TUNING SUGGESTIONS
// ==========================================

/** Get tuning suggestions */
router.get("/tuning-suggestions", async (req: Request, res: Response) => {
  try {
    const { agent_id } = req.query;
    const result = await pool.query(
      agent_id
        ? "SELECT * FROM tuning_suggestions WHERE agent_id = $1 ORDER BY created_at DESC"
        : "SELECT * FROM tuning_suggestions ORDER BY created_at DESC",
      agent_id ? [agent_id] : []
    );
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching suggestions:", err);
    res.status(500).json({ error: "Failed to fetch tuning suggestions" });
  }
});

export default router;
