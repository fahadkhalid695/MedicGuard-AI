import { useEffect, useState } from "react";
import type { AlertEvent } from "../types";

interface Props {
  alert: AlertEvent | null;
  onDismiss: () => void;
}

export function NotificationBar({ alert, onDismiss }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (alert && alert.severity === "critical") {
      setVisible(true);
    }
  }, [alert]);

  if (!visible || !alert) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-pulse-critical">
      <div className="bg-red-600 text-white px-6 py-3 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🚨</span>
          <div>
            <p className="font-bold text-sm uppercase tracking-wide">
              Critical Alert
            </p>
            <p className="text-sm opacity-90">{alert.summary}</p>
          </div>
        </div>
        <button
          onClick={() => {
            setVisible(false);
            onDismiss();
          }}
          className="px-4 py-1.5 bg-red-700 hover:bg-red-800 rounded-lg text-sm font-medium transition-colors"
          aria-label="Dismiss alert"
        >
          Acknowledge
        </button>
      </div>
    </div>
  );
}
