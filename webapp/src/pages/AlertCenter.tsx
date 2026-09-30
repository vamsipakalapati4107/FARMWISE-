import { useQuery, useQueryClient } from "@tanstack/react-query"
import { CheckCircle2 } from "lucide-react"
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"

import { EmptyState } from "@/components/EmptyState"
import { ErrorState } from "@/components/ErrorState"
import { LoadingState } from "@/components/LoadingState"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { AlertSeverity4, AlertStatus, FarmAlert } from "@/lib/api"
import { getAlertCenterAlerts, markAlertRead, resolveAlert } from "@/lib/api"
import { cn } from "@/lib/utils"

const SEVERITY_META: Record<AlertSeverity4, { emoji: string; label: string; text: string; bg: string; border: string }> = {
  critical: { emoji: "\u{1F534}", label: "Critical", text: "text-status-critical", bg: "bg-status-critical-bg", border: "border-status-critical" },
  warning: { emoji: "\u{1F7E0}", label: "Warning", text: "text-status-warning", bg: "bg-status-warning-bg", border: "border-status-warning" },
  attention: { emoji: "\u{1F7E1}", label: "Attention", text: "text-status-warning", bg: "bg-status-warning-bg", border: "border-status-warning" },
  info: { emoji: "\u{1F7E2}", label: "Information", text: "text-status-safe", bg: "bg-status-safe-bg", border: "border-status-safe" },
}

const SOURCE_LABELS: Record<string, string> = {
  weather_observation: "Weather Observation",
  weather_forecast: "Weather Forecast",
  ml_prediction: "ML Prediction",
  spatial_estimation: "Spatial Estimate",
  derived_assessment: "Derived Risk Assessment",
  advisory_engine: "AI Farm Advisor",
}

function AlertCard({ alert, onRead, onResolve }: { alert: FarmAlert; onRead: () => void; onResolve: () => void }) {
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
        <div>
          <dt className="font-medium text-charcoal">Reason</dt>
          <dd className="text-graphite">{alert.reason}</dd>
        </div>
        <div>
          <dt className="font-medium text-charcoal">Recommended Action</dt>
          <dd className="text-graphite">{alert.recommended_action}</dd>
        </div>
        <div className="flex items-center justify-between text-xs text-pewter">
          <span>Source: {SOURCE_LABELS[alert.source] ?? alert.source}</span>
          {alert.valid_until && <span>Concerns: {alert.valid_until}</span>}
        </div>
      </dl>

      <div className="mt-4 flex gap-2">
        {alert.status === "new" && (
          <Button size="sm" variant="outline" onClick={onRead}>
            Mark as Read
          </Button>
        )}
        {alert.status !== "resolved" && (
          <Button size="sm" onClick={onResolve}>
            Resolve
          </Button>
        )}
      </div>
    </div>
  )
}

export function AlertCenter() {
  const queryClient = useQueryClient()
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["alert-center"], queryFn: getAlertCenterAlerts })

  const [severityFilter, setSeverityFilter] = useState<AlertSeverity4 | "all">("all")
  const [statusFilter, setStatusFilter] = useState<AlertStatus | "all">("all")
  const [farmFilter, setFarmFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")

  const alerts = data ?? []
  const farmOptions = useMemo(() => [...new Set(alerts.map((a) => a.farm_name))], [alerts])
  const typeOptions = useMemo(() => [...new Set(alerts.map((a) => a.alert_type))], [alerts])

  const filtered = alerts.filter((a) => {
    if (severityFilter !== "all" && a.severity !== severityFilter) return false
    if (statusFilter !== "all" && a.status !== statusFilter) return false
    if (farmFilter !== "all" && a.farm_name !== farmFilter) return false
    if (typeFilter !== "all" && a.alert_type !== typeFilter) return false
    return true
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["alert-center"] })

  if (isLoading) return <LoadingState label="Loading alerts..." />
  if (isError) return <ErrorState message="Unable to load alerts right now." onRetry={() => refetch()} />

  const counts = {
    critical: alerts.filter((a) => a.severity === "critical" && a.status !== "resolved" && a.status !== "expired").length,
    warning: alerts.filter((a) => a.severity === "warning" && a.status !== "resolved" && a.status !== "expired").length,
    attention: alerts.filter((a) => a.severity === "attention" && a.status !== "resolved" && a.status !== "expired").length,
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-medium text-charcoal">🔔 Alert Center</h1>
        <p className="mt-1 text-sm text-graphite">
          {counts.critical} Critical · {counts.warning} Warning · {counts.attention} Attention
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Select value={severityFilter} onValueChange={(v) => v && setSeverityFilter(v as AlertSeverity4 | "all")}>
          <SelectTrigger className="w-40" size="sm">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Severity: All</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
            <SelectItem value="warning">Warning</SelectItem>
            <SelectItem value="attention">Attention</SelectItem>
            <SelectItem value="info">Information</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={(v) => v && setStatusFilter(v as AlertStatus | "all")}>
          <SelectTrigger className="w-40" size="sm">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Status: All</SelectItem>
            <SelectItem value="new">New</SelectItem>
            <SelectItem value="read">Read</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="expired">Expired</SelectItem>
          </SelectContent>
        </Select>

        <Select value={farmFilter} onValueChange={(v) => v && setFarmFilter(v)}>
          <SelectTrigger className="w-40" size="sm">
            <SelectValue placeholder="Farm" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Farm: All</SelectItem>
            {farmOptions.map((f) => (
              <SelectItem key={f} value={f}>
                {f}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={typeFilter} onValueChange={(v) => v && setTypeFilter(v)}>
          <SelectTrigger className="w-44" size="sm">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Type: All</SelectItem>
            {typeOptions.map((t) => (
              <SelectItem key={t} value={t}>
                {t.replace(/_/g, " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          message={
            alerts.length === 0
              ? "Your farms currently have no important conditions requiring attention."
              : "No alerts match the current filters."
          }
        />
      ) : (
        <div className="space-y-4">
          {filtered.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onRead={async () => {
                await markAlertRead(alert.id)
                invalidate()
              }}
              onResolve={async () => {
                await resolveAlert(alert.id)
                invalidate()
              }}
            />
          ))}
        </div>
      )}

      {alerts.some((a) => a.plot_id) && (
        <p className="text-xs text-pewter">
          <Link to="/farm" className="text-forest-ink hover:underline">
            View My Farm
          </Link>{" "}
          for plot-level details.
        </p>
      )}
    </div>
  )
}
