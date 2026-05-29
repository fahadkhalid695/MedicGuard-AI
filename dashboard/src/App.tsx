import { useState, useEffect } from "react";
import { AccuracyTrendsChart } from "./components/AccuracyTrendsChart";
import { FalsePositiveChart } from "./components/FalsePositiveChart";
import { ABComparisonPanel } from "./components/ABComparisonPanel";
import { SummaryCards } from "./components/SummaryCards";
import {
  fetchPerformanceSummary,
  fetchPerformanceTrends,
  type PerformanceSummary,
  type PerformanceTrend,
} from "./api";

export default function App() {
  const [summaries, setSummaries] = useState<PerformanceSummary[]>([]);
  const [trends, setTrends] = useState<PerformanceTrend[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load summary on mount
  useEffect(() => {
    fetchPerformanceSummary()
      .then((data) => {
        setSummaries(data);
        if (data.length > 0 && !selectedAgent) {
          setSelectedAgent(data[0].agent_id);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Load trends when agent changes
  useEffect(() => {
    if (!selectedAgent) return;
    setLoading(true);
    fetchPerformanceTrends(selectedAgent, 16)
      .then(setTrends)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedAgent]);

  const agents = summaries.map((s) => s.agent_id);
  const currentSummary = summaries.find((s) => s.agent_id === selectedAgent);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>MediGuard AI — Agent Accuracy Dashboard</h1>
        <p>Feedback loop performance metrics and threshold tuning</p>
      </header>

      {error && <div className="error">{error}</div>}

      {/* Agent selector */}
      {agents.length > 0 && (
        <div className="agent-selector">
          {agents.map((agent) => (
            <button
              key={agent}
              className={agent === selectedAgent ? "active" : ""}
              onClick={() => setSelectedAgent(agent)}
            >
              {agent}
            </button>
          ))}
        </div>
      )}

      {/* Summary cards */}
      {currentSummary && <SummaryCards summary={currentSummary} />}

      {loading ? (
        <div className="loading">Loading performance data...</div>
      ) : (
        <>
          {/* Main charts */}
          <div className="chart-grid">
            <div className="chart-section">
              <h2>Precision, Recall & F1 Score Over Time</h2>
              <AccuracyTrendsChart data={trends} />
            </div>

            <div className="chart-section">
              <h2>False Positive Rate Trend</h2>
              <FalsePositiveChart data={trends} />
            </div>
          </div>

          {/* A/B Comparison */}
          <div className="chart-section">
            <h2>A/B Test Comparison</h2>
            <ABComparisonPanel agentId={selectedAgent} trends={trends} />
          </div>
        </>
      )}
    </div>
  );
}
