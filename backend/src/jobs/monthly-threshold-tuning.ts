/**
 * Monthly Threshold Tuning Job
 *
 * Runs on the 1st of each month at 3:00 AM. Collects the last 30 days of
 * performance data and calls Claude API to suggest updated thresholds.
 *
 * Usage:
 *   npx tsx src/jobs/monthly-threshold-tuning.ts       # run manually
 *   Scheduled via node-cron in server.ts               # automatic
 */

import Anthropic from "@anthropic-ai/sdk";
import { v4 as uuidv4 } from "uuid";
import pool from "../db.js";
import type { VitalThresholds } from "../types.js";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

interface PerformanceDataForClaude {
  agent_id: string;
  current_thresholds: VitalThresholds;
  metrics_by_condition: Array<{
    condition_type: string | null;
    precision_rate: number | null;
    recall_rate: number | null;
    false_positive_rate: number | null;
    f1_score: number | null;
    total_alerts: number;
    doctor_overrides: number;
  }>;
  overall_metrics: {
    precision_rate: number | null;
    recall_rate: number | null;
    false_positive_rate: number | null;
    f1_score: number | null;
    total_alerts: number;
  };
}

async function gatherPerformanceData(agentId: string): Promise<PerformanceDataForClaude | null> {
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

  // Get current thresholds
  const thresholdResult = await pool.query(
    "SELECT * FROM threshold_configs WHERE agent_id = $1 AND is_active = TRUE LIMIT 1",
    [agentId]
  );

  if (thresholdResult.rows.length === 0) {
    console.log(`[MonthlyTuning] No active threshold config for agent ${agentId}, skipping.`);
    return null;
  }

  const currentThresholds = thresholdResult.rows[0].thresholds;

  // Get performance metrics by condition
  const metricsResult = await pool.query(
    `SELECT condition_type, precision_rate, recall_rate, false_positive_rate,
            f1_score, total_alerts, doctor_overrides
     FROM agent_performance
     WHERE agent_id = $1 AND period_start >= $2
     ORDER BY period_start DESC`,
    [agentId, thirtyDaysAgo.toISOString().split("T")[0]]
  );

  // Separate overall vs per-condition
  const byCondition = metricsResult.rows.filter((r: { condition_type: string | null }) => r.condition_type !== null);
  const overall = metricsResult.rows.find((r: { condition_type: string | null }) => r.condition_type === null);

  return {
    agent_id: agentId,
    current_thresholds: currentThresholds,
    metrics_by_condition: byCondition,
    overall_metrics: overall || {
      precision_rate: null,
      recall_rate: null,
      false_positive_rate: null,
      f1_score: null,
      total_alerts: 0,
    },
  };
}

async function callClaudeForSuggestions(
  data: PerformanceDataForClaude
): Promise<{ suggested_thresholds: VitalThresholds; reasoning: string }> {
  const prompt = `You are a clinical AI threshold optimization assistant for MediGuard AI, a patient monitoring system.

Given this agent performance data, suggest updated thresholds for each vital sign to reduce false positives while maintaining sensitivity for critical events.

## Current Configuration

Agent: ${data.agent_id}

### Current Thresholds:
${JSON.stringify(data.current_thresholds, null, 2)}

### Overall Performance (last 30 days):
- Precision: ${data.overall_metrics.precision_rate ?? "N/A"}
- Recall: ${data.overall_metrics.recall_rate ?? "N/A"}
- False Positive Rate: ${data.overall_metrics.false_positive_rate ?? "N/A"}
- F1 Score: ${data.overall_metrics.f1_score ?? "N/A"}
- Total Alerts: ${data.overall_metrics.total_alerts}

### Performance by Condition Type:
${JSON.stringify(data.metrics_by_condition, null, 2)}

## Requirements:
1. CRITICAL thresholds should remain conservative (high sensitivity) — missing a critical event is worse than a false alarm.
2. Non-critical thresholds can be relaxed if false positive rate is high.
3. If precision is below 0.7, widen the normal range to reduce noise.
4. If recall is below 0.9 for any condition, tighten thresholds for that vital.
5. Doctor override rate above 20% strongly suggests thresholds are too aggressive.

## Response Format:
Respond with a JSON object containing:
- "suggested_thresholds": the full updated threshold object (same structure as current)
- "reasoning": a brief explanation of each change made and why

Return ONLY valid JSON, no markdown fences.`;

  const response = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 2000,
    messages: [{ role: "user", content: prompt }],
  });

  const text = response.content[0].type === "text" ? response.content[0].text : "";

  try {
    return JSON.parse(text);
  } catch {
    // Try to extract JSON from the response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }
    throw new Error(`Failed to parse Claude response: ${text.substring(0, 200)}`);
  }
}

export async function runMonthlyThresholdTuning(): Promise<void> {
  console.log("[MonthlyTuning] Starting threshold tuning job...");

  // Get all distinct agents that have performance data
  const agentsResult = await pool.query(
    "SELECT DISTINCT agent_id FROM agent_performance"
  );

  for (const { agent_id } of agentsResult.rows) {
    console.log(`[MonthlyTuning] Processing agent: ${agent_id}`);

    try {
      const data = await gatherPerformanceData(agent_id);
      if (!data) continue;

      const suggestion = await callClaudeForSuggestions(data);

      // Store the suggestion
      await pool.query(
        `INSERT INTO tuning_suggestions (id, agent_id, performance_data, suggestion)
         VALUES ($1, $2, $3, $4)`,
        [
          uuidv4(),
          agent_id,
          JSON.stringify(data),
          JSON.stringify(suggestion),
        ]
      );

      // Create a new threshold config (not active — requires admin approval)
      const version = `claude-${new Date().toISOString().split("T")[0]}-${agent_id}`;
      await pool.query(
        `INSERT INTO threshold_configs (id, version, agent_id, thresholds, source, is_active, notes)
         VALUES ($1, $2, $3, $4, 'claude_suggested', FALSE, $5)`,
        [
          uuidv4(),
          version,
          agent_id,
          JSON.stringify(suggestion.suggested_thresholds),
          suggestion.reasoning,
        ]
      );

      console.log(`[MonthlyTuning] Suggestion stored for ${agent_id} as version: ${version}`);
    } catch (err) {
      console.error(`[MonthlyTuning] Error processing agent ${agent_id}:`, err);
    }
  }

  console.log("[MonthlyTuning] Completed.");
}

// Allow direct execution
if (process.argv[1]?.includes("monthly-threshold-tuning")) {
  runMonthlyThresholdTuning()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}
