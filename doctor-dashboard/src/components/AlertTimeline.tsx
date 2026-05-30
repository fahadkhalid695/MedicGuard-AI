import type { AlertEvent } from "../types";
import { severityBorder, severityColor, formatTimeShort, timeAgo } from "../utils";

interface Props {
  alerts: AlertEvent[];
}

export function AlertTimeline({ alerts }: Props) {
  if (alerts.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Alert History — Last 24h
        </h3>
        <p className="text-sm text-gray-400">No alerts in the last 24 hours.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Alert History — Last 24h
      </h3>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`border-l-4 ${severityBorder(alert.severity)} bg-gray-50 rounded-r-lg p-3 flex items-start justify-between`}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className={`severity-badge text-[10px] ${severityColor(alert.severity)}`}>
                  {alert.severity.toUpperCase()}
                </span>
                <span className="text-xs text-gray-400">
                  {formatTimeShort(alert.timestamp)}
                </span>
              </div>
              <p className="text-sm text-gray-700 truncate">{alert.title}</p>
              {alert.summary && (
                <p className="text-xs text-gray-500 mt-0.5 truncate">
                  {alert.summary}
                </p>
              )}
            </div>
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                alert.status === "active"
                  ? "bg-red-100 text-red-700"
                  : alert.status === "acknowledged"
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-green-100 text-green-700"
              }`}
            >
              {alert.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
