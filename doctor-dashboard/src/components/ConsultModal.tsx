import { useState } from "react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { scheduledAt: string; telehealthLink: string; notes: string }) => void;
  patientName: string;
}

export function ConsultModal({ isOpen, onClose, onSubmit, patientName }: Props) {
  const [scheduledAt, setScheduledAt] = useState("");
  const [telehealthLink, setTelehealthLink] = useState("https://meet.mediguard.ai/");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduledAt) return;
    setSubmitting(true);
    onSubmit({ scheduledAt, telehealthLink, notes });
    // Reset form
    setScheduledAt("");
    setNotes("");
    setSubmitting(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md p-6 mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">Schedule Emergency Consult</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        <p className="text-sm text-gray-500 mb-4">
          Patient: <span className="font-medium text-gray-700">{patientName}</span>
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Date/Time picker */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date & Time
            </label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-clinical-500 focus:border-clinical-500 outline-none"
            />
          </div>

          {/* Telehealth link */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Telehealth Link
            </label>
            <input
              type="url"
              value={telehealthLink}
              onChange={(e) => setTelehealthLink(e.target.value)}
              placeholder="https://meet.mediguard.ai/room-id"
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-clinical-500 focus:border-clinical-500 outline-none"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Reason for consult, preparation needed..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-clinical-500 focus:border-clinical-500 outline-none resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !scheduledAt}
              className="flex-1 px-4 py-2 bg-clinical-600 text-white rounded-lg text-sm font-medium hover:bg-clinical-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? "Scheduling..." : "Schedule Consult"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
