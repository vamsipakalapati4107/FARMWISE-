import { CloudRain, ShieldAlert, Sun } from "lucide-react"

import { RiskIndicator } from "@/components/RiskIndicator"
import type { Severity } from "@/lib/advisory"
import { SEVERITY_STYLES } from "@/lib/advisory"
import { cn } from "@/lib/utils"

const ICONS = {
  critical: CloudRain,
  warning: ShieldAlert,
  safe: Sun,
} as const

export interface WeatherAlertProps {
  severity: Severity
  title: string
  description: string
  action: string
  dateLabel: string
}

export function WeatherAlert({ severity, title, description, action, dateLabel }: WeatherAlertProps) {
  const style = SEVERITY_STYLES[severity]
  const Icon = ICONS[severity]

  return (
    <div
      className={cn(
        "flex gap-4 rounded-card border-l-4 bg-card p-6",
        style.border
      )}
    >
      <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-full", style.bg)}>
        <Icon className={cn("size-5", style.text)} aria-hidden="true" />
      </div>
      <div className="flex-1 space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-serif text-lg font-medium text-charcoal">{title}</h3>
          <RiskIndicator severity={severity} />
        </div>
        <p className="text-sm text-graphite">{description}</p>
        <p className="text-sm font-medium text-forest-ink">{action}</p>
        <p className="text-xs text-pewter">{dateLabel}</p>
      </div>
    </div>
  )
}
