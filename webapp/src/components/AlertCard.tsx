import { Button } from "@/components/ui/button"
import type { AlertSeverity4, FarmAlert } from "@/lib/api"
import { cn } from "@/lib/utils"

export const SEVERITY_META: Record<
  AlertSeverity4,
  { emoji: string; label: string; text: string; bg: string; border: string }
> = {
  critical: { emoji: "\u{1F534}", label: "Critical", text: "text-status-critical", bg: "bg-status-critical-bg", border: "border-status-critical" },
  warning: { emoji: "\u{1F7E0}", label: "Warning", text: "text-status-warning", bg: "bg-status-warning-bg", border: "border-status-warning" },
  attention: { emoji: "\u{1F7E1}", label: "Attention", text: "text-status-warning", bg: "bg-status-warning-bg", border: "border-status-warning" },
  info: { emoji: "\u{1F7E2}", label: "Information", text: "text-status-safe", bg: "bg-status-safe-bg", border: "border-status-safe" },
}

export const SOURCE_LABELS: Record<string, string> = {
  weather_observation: "Weather Observation",
  weather_forecast: "Weather Forecast",
  ml_prediction: "ML Prediction",
  spatial_estimation: "Spatial Estimate",
  derived_assessment: "Derived Risk Assessment",
  advisory_engine: "AI Farm Advisor",
}

const SMS_STATUS_LABELS: Record<FarmAlert["sms"]["status"], string> = {
  SENT: "Sent",
  DELIVERED: "Delivered",
  FAILED: "Failed",
  NOT_SENT: "Pending",
  DISABLED: "Disabled",
  NOT_APPLICABLE: "Not applicable",
}

/** Shared with the full Alert Center page and the Home page's compact
 * alert widget -- one card implementation, not duplicated. */
export function AlertCard({
  alert,
  onRead,
  onResolve,
  compact = false,
}: {
  alert: FarmAlert
  onRead?: () => void
  onResolve?: () => void
  compact?: boolean
}) {
  const meta = SEVERITY_META[alert.severity]
  return (
    <div className={cn("rounded-card border-l-4 bg-card p-5", meta.border, alert.status === "resolved" && "opacity-60")}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-serif text-base font-medium text-charcoal">
            {meta.emoji} {alert.title}
          </p>
          <p className="text-xs text-graphite">
            {alert.crop_name && `${alert.crop_name} · `}
            {alert.plot_name ?? alert.farm_name}
          </p>
        </div>
        <span className={cn("rounded-full px-3 py-1 text-xs font-medium", meta.bg, meta.text)}>{meta.label}</span>
      </div>

      <dl className="mt-3 space-y-1.5 text-sm">
        {!compact && (
          <div>
            <dt className="font-medium text-charcoal">Reason</dt>
            <dd className="text-graphite">{alert.reason}</dd>
          </div>
        )}
        <div>
          <dt className="font-medium text-charcoal">Recommended Action</dt>
          <dd className="text-graphite">{alert.recommended_action}</dd>
        </div>
        <div className="flex items-center justify-between text-xs text-pewter">
          <span>Source: {SOURCE_LABELS[alert.source] ?? alert.source}</span>
          {alert.valid_until && <span>Concerns: {alert.valid_until}</span>}
        </div>
        {alert.sms.status !== "NOT_APPLICABLE" && (
          <div className="text-xs text-pewter">
            📱 SMS: {SMS_STATUS_LABELS[alert.sms.status]}
            {alert.sms.simulated && alert.sms.status !== "DISABLED" && alert.sms.status !== "NOT_SENT" && " (simulated)"}
          </div>
        )}
      </dl>

      {(onRead || onResolve) && (
        <div className="mt-4 flex gap-2">
          {alert.status === "new" && onRead && (
            <Button size="sm" variant="outline" onClick={onRead}>
              Mark as Read
            </Button>
          )}
          {alert.status !== "resolved" && onResolve && (
            <Button size="sm" onClick={onResolve}>
              Resolve
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
