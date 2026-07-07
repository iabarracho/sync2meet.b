import { cn } from "@/lib/utils";
import type { MeetingStatus } from "@/lib/api";
import { STATUS_LABELS } from "@/lib/api";

const statusColors: Record<MeetingStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  agenda_ready: "bg-blue-100 text-blue-800",
  in_progress: "bg-amber-100 text-amber-800",
  recorded: "bg-purple-100 text-purple-800",
  processing: "bg-orange-100 text-orange-800",
  minutes_ready: "bg-cyan-100 text-cyan-800",
  pending_approval: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  distributed: "bg-emerald-100 text-emerald-900",
};

export function StatusBadge({ status }: { status: MeetingStatus }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium",
        statusColors[status]
      )}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
