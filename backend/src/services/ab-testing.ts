import { v4 as uuidv4 } from "uuid";
import pool from "../db.js";
import type { ABGroup, ABTest, ThresholdConfig } from "../types.js";

/**
 * Create a new A/B test with two threshold configurations.
 */
export async function createABTest(params: {
  name: string;
  description?: string;
  agent_id: string;
  config_a_id: string;
  config_b_id: string;
  start_date?: string;
  end_date?: string;
}): Promise<ABTest> {
  const id = uuidv4();

  const result = await pool.query(
    `INSERT INTO ab_tests (id, name, description, agent_id, config_a_id, config_b_id, start_date, end_date)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
     RETURNING *`,
    [id, params.name, params.description, params.agent_id, params.config_a_id, params.config_b_id, params.start_date, params.end_date]
  );

  // Mark both configs with their A/B group
  await pool.query("UPDATE threshold_configs SET ab_group = 'A' WHERE id = $1", [params.config_a_id]);
  await pool.query("UPDATE threshold_configs SET ab_group = 'B' WHERE id = $1", [params.config_b_id]);

  return result.rows[0];
}

/**
 * Assign patients to A/B groups (random 50/50 split).
 */
export async function assignPatientsToABTest(
  abTestId: string,
  patientIds: string[]
): Promise<{ groupA: string[]; groupB: string[] }> {
  const shuffled = [...patientIds].sort(() => Math.random() - 0.5);
  const midpoint = Math.ceil(shuffled.length / 2);

  const groupA = shuffled.slice(0, midpoint);
  const groupB = shuffled.slice(midpoint);

  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    for (const pid of groupA) {
      await client.query(
        `INSERT INTO ab_patient_groups (id, ab_test_id, patient_id, ab_group)
         VALUES ($1, $2, $3, 'A')
         ON CONFLICT (ab_test_id, patient_id) DO UPDATE SET ab_group = 'A'`,
        [uuidv4(), abTestId, pid]
      );
    }

    for (const pid of groupB) {
      await client.query(
        `INSERT INTO ab_patient_groups (id, ab_test_id, patient_id, ab_group)
         VALUES ($1, $2, $3, 'B')
         ON CONFLICT (ab_test_id, patient_id) DO UPDATE SET ab_group = 'B'`,
        [uuidv4(), abTestId, pid]
      );
    }

    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }

  return { groupA, groupB };
}

/**
 * Get the active threshold config for a patient (checks A/B group).
 */
export async function getThresholdForPatient(
  patientId: string,
  agentId: string
): Promise<ThresholdConfig | null> {
  // Check if patient is in an active A/B test
  const abResult = await pool.query(
    `SELECT apg.ab_group, abt.config_a_id, abt.config_b_id
     FROM ab_patient_groups apg
     JOIN ab_tests abt ON abt.id = apg.ab_test_id
     WHERE apg.patient_id = $1 AND abt.agent_id = $2 AND abt.status = 'running'
     LIMIT 1`,
    [patientId, agentId]
  );

  if (abResult.rows.length > 0) {
    const { ab_group, config_a_id, config_b_id } = abResult.rows[0];
    const configId = ab_group === "A" ? config_a_id : config_b_id;

    const configResult = await pool.query(
      "SELECT * FROM threshold_configs WHERE id = $1",
      [configId]
    );
    return configResult.rows[0] || null;
  }

  // No A/B test — return the active config for this agent
  const configResult = await pool.query(
    "SELECT * FROM threshold_configs WHERE agent_id = $1 AND is_active = TRUE LIMIT 1",
    [agentId]
  );
  return configResult.rows[0] || null;
}

/**
 * Start an A/B test (set status to running).
 */
export async function startABTest(abTestId: string): Promise<void> {
  await pool.query(
    "UPDATE ab_tests SET status = 'running', start_date = CURRENT_DATE WHERE id = $1",
    [abTestId]
  );
}

/**
 * Complete an A/B test and optionally promote the winner.
 */
export async function completeABTest(
  abTestId: string,
  winner?: ABGroup
): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    await client.query(
      "UPDATE ab_tests SET status = 'completed', end_date = CURRENT_DATE WHERE id = $1",
      [abTestId]
    );

    if (winner) {
      // Get the winning config and promote it
      const test = await client.query("SELECT * FROM ab_tests WHERE id = $1", [abTestId]);
      const winningConfigId = winner === "A" ? test.rows[0].config_a_id : test.rows[0].config_b_id;
      const agentId = test.rows[0].agent_id;

      // Deactivate current active config
      await client.query(
        "UPDATE threshold_configs SET is_active = FALSE, deactivated_at = NOW() WHERE agent_id = $1 AND is_active = TRUE",
        [agentId]
      );

      // Activate the winner
      await client.query(
        "UPDATE threshold_configs SET is_active = TRUE, activated_at = NOW(), source = 'ab_winner' WHERE id = $1",
        [winningConfigId]
      );
    }

    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

/**
 * Get A/B test results (performance comparison between groups).
 */
export async function getABTestResults(abTestId: string) {
  const result = await pool.query(
    `SELECT
       ap.ab_group,
       COUNT(*) as total_alerts,
       SUM(CASE WHEN ao.outcome = 'true_positive' THEN 1 ELSE 0 END) as true_positives,
       SUM(CASE WHEN ao.outcome = 'false_positive' THEN 1 ELSE 0 END) as false_positives,
       SUM(CASE WHEN ao.outcome = 'doctor_override' THEN 1 ELSE 0 END) as doctor_overrides,
       AVG(ao.time_to_review_min) as avg_review_time_min
     FROM ab_patient_groups apg
     JOIN alert_outcomes ao ON ao.patient_id = apg.patient_id
     JOIN agent_performance ap ON ap.ab_group = apg.ab_group
     WHERE apg.ab_test_id = $1
     GROUP BY ap.ab_group`,
    [abTestId]
  );

  return result.rows;
}
