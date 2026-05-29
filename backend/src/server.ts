import express from "express";
import cors from "cors";
import cron from "node-cron";
import feedbackRoutes from "./routes/feedback.js";
import { runWeeklyAccuracyReport } from "./jobs/weekly-accuracy-report.js";
import { runMonthlyThresholdTuning } from "./jobs/monthly-threshold-tuning.js";

const app = express();
const PORT = parseInt(process.env.PORT || "3001");

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use("/api/feedback", feedbackRoutes);

// Health check
app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// ==========================================
// SCHEDULED JOBS
// ==========================================

// Weekly accuracy report: every Monday at 2:00 AM
cron.schedule("0 2 * * 1", async () => {
  console.log("[Cron] Running weekly accuracy report...");
  try {
    await runWeeklyAccuracyReport();
  } catch (err) {
    console.error("[Cron] Weekly report failed:", err);
  }
});

// Monthly threshold tuning: 1st of each month at 3:00 AM
cron.schedule("0 3 1 * *", async () => {
  console.log("[Cron] Running monthly threshold tuning...");
  try {
    await runMonthlyThresholdTuning();
  } catch (err) {
    console.error("[Cron] Monthly tuning failed:", err);
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`MediGuard Feedback API running on port ${PORT}`);
  console.log("Scheduled jobs:");
  console.log("  - Weekly accuracy report: Mon 2:00 AM");
  console.log("  - Monthly threshold tuning: 1st of month 3:00 AM");
});

export default app;
