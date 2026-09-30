import { useState } from "react"
import {
  Bug,
  ChevronDown,
  CloudRain,
  ClipboardList,
  Droplets,
  Search,
  Sprout,
} from "lucide-react"

import type { Recommendation, RecommendationCategory, RecommendationStatus } from "@/lib/api"
import { cn } from "@/lib/utils"

const CATEGORY_META: Record<RecommendationCategory, { label: string; icon: typeof Droplets }> = {
  irrigation: { label: "Irrigation", icon: Droplets },
  fertilizer: { label: "Fertilizer", icon: Sprout },
  disease_monitoring: { label: "Disease Monitoring", icon: Bug },
  field_inspection: { label: "Field Inspection", icon: Search },
  weather_precautions: { label: "Weather Precautions", icon: CloudRain },
  general_operations: { label: "General Operations", icon: ClipboardList },
}

const STATUS_STYLES: Record<RecommendationStatus, { label: string; text: string; bg: string; border: string }> = {
  avoid: { label: "Avoid", text: "text-status-critical", bg: "bg-status-critical-bg", border: "border-status-critical" },
  delay: { label: "Delay", text: "text-status-warning", bg: "bg-status-warning-bg", border: "border-status-warning" },
  recommended: { label: "Recommended", text: "text-status-info", bg: "bg-status-info-bg", border: "border-status-info" },
  monitor: { label: "Monitor", text: "text-status-warning", bg: "bg-status-warning-bg", border: "border-status-warning" },
  normal: { label: "Normal", text: "text-status-safe", bg: "bg-status-safe-bg", border: "border-status-safe" },
}

export function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const [open, setOpen] = useState(false)
  const { label, icon: Icon } = CATEGORY_META[recommendation.category]
  const style = STATUS_STYLES[recommendation.status]

  return (
    <div className={cn("rounded-card border-l-4 bg-card p-5", style.border)}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-forest-ink" aria-hidden="true" />
          <h3 className="font-serif text-base font-medium text-charcoal">{label}</h3>
        </div>
        <span className={cn("rounded-full px-3 py-1 text-xs font-medium", style.bg, style.text)}>{style.label}</span>
      </div>

      <p className="mt-2 text-sm text-graphite">{recommendation.what}</p>

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="mt-2 flex items-center gap-1 text-xs font-medium text-forest-ink"
      >
        Why this recommendation?
        <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden="true" />
      </button>

      {open && (
        <dl className="mt-3 space-y-2 border-t border-moss/30 pt-3 text-sm">
          <div>
            <dt className="font-medium text-charcoal">Why?</dt>
            <dd className="text-graphite">{recommendation.why}</dd>
          </div>
          <div>
            <dt className="font-medium text-charcoal">When?</dt>
            <dd className="text-graphite">{recommendation.when}</dd>
          </div>
        </dl>
      )}
    </div>
  )
}

export { CATEGORY_META, STATUS_STYLES }
