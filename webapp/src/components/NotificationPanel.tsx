import { Bell } from "lucide-react"

import { EmptyState } from "@/components/EmptyState"
import type { AppNotification } from "@/lib/api"
import { cn } from "@/lib/utils"

const DOT_COLOR: Record<AppNotification["severity"], string> = {
  critical: "bg-status-critical",
  warning: "bg-status-warning",
  safe: "bg-status-safe",
  info: "bg-status-info",
}

export function NotificationPanel({
  notifications,
  onMarkRead,
}: {
  notifications: AppNotification[]
  onMarkRead: (id: string) => void
}) {
  if (notifications.length === 0) {
    return <EmptyState icon={Bell} message="No notifications yet." />
  }

  return (
    <div className="divide-y divide-moss/40 rounded-card bg-card">
      {notifications.map((n) => (
        <button
          key={n.id}
          type="button"
          onClick={() => onMarkRead(n.id)}
          className={cn(
            "flex w-full items-start gap-3 px-5 py-4 text-left transition-colors hover:bg-ash-gray/60",
            !n.read && "bg-sky-card/20"
          )}
        >
          <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", DOT_COLOR[n.severity])} aria-hidden="true" />
          <div className="flex-1">
            <p className={cn("text-sm", n.read ? "text-graphite" : "font-medium text-charcoal")}>{n.title}</p>
            <p className="text-sm text-pewter">{n.body}</p>
            <p className="mt-1 text-xs text-pewter">
              {new Date(n.created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
            </p>
          </div>
        </button>
      ))}
    </div>
  )
}
