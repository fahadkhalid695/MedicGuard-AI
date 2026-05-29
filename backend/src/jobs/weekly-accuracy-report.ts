/**
 * Weekly Accuracy Report Job
 *
 * Runs every Monday at 2:00 AM. Calculates precision, recall, and false positive
 * rate per agent and per condition type for the previous week.
 * Results are stored in the agent_performance table.
 *
 * Usage:
 *   npx tsx src/jobs/weekly-accuracy-report.ts          # run manually
 *   Scheduled via node-cron in server.ts                # automatic
 */

import { v4 as uuidv4 } from "uuid";
import pool from "../db.js";

interface PerformanceMetrics {
  total_alerts: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  doctor_overrides: number;
  precision_rate: number | null;
  recall_rate: number | null;
  false_positive_rate: number | null;
  f1_score: number | null;
}

function calculateMetrics(
  tp: number,
  fp: number,
  fn: number,
  overrides: number,
  total: number
): PerformanceMetrics {
  const precision = tp + fp > 0 ? tp / (tp + fp) : null;
  const recall = tp + fn > 0 ? tp / (tp + fn) : null;
  const fpr = fp + tp > 0 ? fp / (fp + tp) : null; // simplified FPR
  const f1 = precision && recall ? (2 * precision * recall) / (precision + recall) : null;

  return {
    total_alerts: total,
    true_positives: tp,
    false_positives: fp,
    false_negatives: fn,
    doctor_overrides: overrides,
    precision_rate: precision ? Math.round(precision * 10000) / 10000 : null,
    recall_rate: recall ? Math.round(recall * 10000) / 10000 : null,
    false_positive_rate: fpr ? Math.round(fpr * 10000) / 10000 : null,
    f1_score: f1 ? Math.round(f1 * 10000) / 10000 : null,
  };
}

export async function runWeeklyAccuracyReport(
  periodStart?: Date,
  periodEnd?: Date
): Promise<void> {
  // Default: previous 7 days
  const end = periodEnd || new Date();
  const start = periodStart || new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);

  console.log(`[WeeklyReport] Calculating metrics for ${start.toISOString()} to ${end.toISOString()}`);

  // Get all outcomes in the period, grouped by agent and condition
  const outcomes = await pool.query(
    `SELECT
       agent_id,
       condition_type,
       outcome,
       COUNT(*) as count
     FROM alert_outcomes
     WHERE created_at >= $1 AND created_at < $2
     GROUP BY agent_id, condition_type, outcome`,
    [start.toISOString(), end.toISOString()]
  );

  // Also check A/B group membership for each outcome
  const abOutcomes = await pool.query(
    `SELECT
       ao.agent_id,
       ao.condition_type,
       ao.outcome,
       apg.ab_group,
       COUNT(*) as count
     FROM alert_outcomes ao
     LEFT JOIN ab_patient_groups apg ON apg.patient_id = ao.patient_id
     LEFT JOIN ab_tests abt ON abt.id = apg.ab_test_id AND abt.status = 'running'
     WHERE ao.created_at >= $1 AND ao.created_at < $2
     GROUP BY ao.agent_id, ao.condition_type, ao.outcome, apg.ab_group`,
    [start.toISOString(), end.toISOString()]
  );

  // Aggregate by (agent_id, condition_type, ab_group)
  type Key = string;
  const aggregates = new Map<Key, {
    agent_id: string;
    condition_type: string | null;
    ab_group: string | null;
    tp: number; fp: number; fn: number; overrides: number; total: number;
  }>();

  for (const row of abOutcomes.rows) {
    const key = `${row.agent_id}|${row.condition_type || "ALL"}|${row.ab_group || "NONE"}`;
    if (!aggregates.has(key)) {
      aggregates.set(key, {
        agent_id: row.agent_id,
        condition_type: row.condition_type || null,
        ab_group: row.ab_group || null,
        tp: 0, fp: 0, fn: 0, overrides: 0, total: 0,
      });
    }
    const agg = aggregates.get(key)!;
    const count = parseInt(row.count);
    agg.total += count;

    switch (row.outcome) {
      case "true_positive":
      case "patient_worsened":
        agg.tp += count;
        break;
      case "false_positive":
      case "resolved_naturally":
        agg.fp += count;
        break;
      case "false_negative":
        agg.fn += count;
        break;
      case "doctor_override":
        agg.overrides += count;
        agg.fp += count; // overrides count as false positives
        break;
    }
  }

  // Also compute aggregate per agent (all conditions combined)
  const agentAggregates = new Map<string, {
    agent_id: string;
    ab_group: string | null;
    tp: number; fp: number; fn: number; overrides: number; total: number;
  }>();

  for (const [, agg] of aggregates) {
    const key = `${agg.agent_id}|${agg.ab_group || "NONE"}`;
    if (!agentAggregates.has(key)) {
      agentAggregates.set(key, {
        agent_id: agg.agent_id,
        ab_group: agg.ab_group,
        tp: 0, fp: 0, fn: 0, overrides: 0, total: 0,
      });
    }
    const agentAgg = agentAggregates.get(key)!;
    agentAgg.tp += agg.tp;
    agentAgg.fp += agg.fp;
    agentAgg.fn += agg.fn;
    agentAgg.overrides += agg.overrides;
    agentAgg.total += agg.total;
  }

  // Get active threshold version per agent
  const thresholdVersions = await pool.query(
    "SELECT agent_id, version FROM threshold_configs WHERE is_active = TRUE"
  );
  const versionMap = new Map(thresholdVersions.rows.map((r: { agent_id: string; version: string }) => [r.agent_id, r.version]));

  // Insert per-condition metrics
  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    for (const [, agg] of aggregates) {
      const metrics = calculateMetrics(agg.tp, agg.fp, agg.fn, agg.overrides, agg.total);
      await client.query(
        `INSERT INTO agent_performance (
          id, agent_id, condition_type, period_start, period_end,
          total_alerts, true_positives, false_positives, false_negatives, doctor_overrides,
          precision_rate, recall_rate, false_positive_rate, f1_score,
          ab_group, threshold_version
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
        ON CONFLICT (agent_id, condition_type, period_start, period_end, ab_group) DO UPDATE SET
          total_alerts = EXCLUDED.total_alerts,
          true_positives = EXCLUDED.true_positives,
          false_positives = EXCLUDED.false_positives,
          false_negatives = EXCLUDED.false_negatives,
          doctor_overrides = EXCLUDED.doctor_overrides,
          precision_rate = EXCLUDED.precision_rate,
          recall_rate = EXCLUDED.recall_rate,
          false_positive_rate = EXCLUDED.false_positive_rate,
          f1_score = EXCLUDED.f1_score`,
        [
          uuidv4(), agg.agent_id, agg.condition_type,
          start.toISOString().split("T")[0], end.toISOString().split("T")[0],
          metrics.total_alerts, metrics.true_positives, metrics.false_positives,
          metrics.false_negatives, metrics.doctor_overrides,
          metrics.precision_rate, metrics.recall_rate, metrics.false_positive_rate, metrics.f1_score,
          agg.ab_group, versionMap.get(agg.agent_id) || null,
        ]
      );
    }

    // Insert aggregate (all conditions) per agent
    for (const [, agg] of agentAggregates) {
      const metrics = calculateMetrics(agg.tp, agg.fp, agg.fn, agg.overrides, agg.total);
      await client.query(
        `INSERT INTO agent_performance (
          id, agent_id, condition_type, period_start, period_end,
          total_alerts, true_positives, false_positives, false_negatives, doctor_overrides,
          precision_rate, recall_rate, false_positive_rate, f1_score,
          ab_group, threshold_version
        ) VALUES ($1,$2,NULL,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        ON CONFLICT (agent_id, condition_type, period_start, period_end, ab_group) DO UPDATE SET
          total_alerts = EXCLUDED.total_alerts,
          true_positives = EXCLUDED.true_positives,
          false_positives = EXCLUDED.false_positives,
          false_negatives = EXCLUDED.false_negatives,
          doctor_overrides = EXCLUDED.doctor_overrides,
          precision_rate = EXCLUDED.precision_rate,
          recall_rate = EXCLUDED.recall_rate,
          false_positive_rate = EXCLUDED.false_positive_rate,
          f1_score = EXCLUDED.f1_score`,
        [
          uuidv4(), agg.agent_id,
          start.toISOString().split("T")[0], end.toISOString().split("T")[0],
          metrics.total_alerts, metrics.true_positives, metrics.false_positives,
          metrics.false_negatives, metrics.doctor_overrides,
          metrics.precision_rate, metrics.recall_rate, metrics.false_positive_rate, metrics.f1_score,
          agg.ab_group, versionMap.get(agg.agent_id) || null,
        ]
      );
    }

    await client.query("COMMIT");
    console.log(`[WeeklyReport] Stored ${aggregates.size + agentAggregates.size} performance records.`);
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("[WeeklyReport] Failed:", err);
    throw err;
  } finally {
    client.release();
  }
}

// Allow direct execution
if (process.argv[1]?.includes("weekly-accuracy-report")) {
  runWeeklyAccuracyReport()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}
