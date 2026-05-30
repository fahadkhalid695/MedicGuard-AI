import type { AIInsight } from "../types";
import { severityColor, timeAgo } from "../utils";

interface Props {
  insight: AIInsight | null;
}

export function AIInsightPanel({ insight }: Props) {
  if (!insight) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
          <span className="text-base">🤖</span> AI Insight
        </h3>
        <p className="text-sm text-gray-400">
          No active AI assessment. Patient vitals are within normal ranges.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <span className="text-base">🤖</span> AI Insight
        </h3>
        <div className="flex items-center gap-2">
          <span className={`severity-badge ${severityColor(insight.severity)}`}>
            {insight.severity.toUpperCase()}
          </span>
          <span className="text-xs text-gray-400">{timeAgo(insight.timestamp)}</span>
        </div>
      </div>

      {/* Summary */}
      <div className="mb-3">
        <p className="text-sm text-gray-800 leading-relaxed">{insight.summary}</p>
      </div>

      {/* Recommended Action */}
      <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 mb-3">
        <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">
          Recommended Action
        </p>
        <p className="text-sm text-blue-900">{insight.action}</p>
      </div>

      {/* Metadata */}
      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span>Confidence: {(insight.confidence * 100).toFixed(0)}%</span>
        <span>Agents: {insight.agents.join(", ")}</span>
      </div>
    </div>
  );
}
