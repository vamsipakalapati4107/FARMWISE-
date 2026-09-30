import { Cpu, Database, ListChecks, Radio } from "lucide-react"

import type { MlClassification, ValueSource } from "@/lib/api"
import { cn } from "@/lib/utils"

/** Phase 0.5: makes it visually explicit whether a value is a real ML
 * prediction, a rule-based derivation, or a raw/pass-through value --
 * never let a forecast/data value be mistaken for an ML prediction. */

const SOURCE_LABELS: Record<ValueSource, { label: string; icon: typeof Cpu; className: string }> = {
  estimated_downscaled: { label: "Estimated (downscaled)", icon: Cpu, className: "bg-status-info-bg text-status-info" },
  gp_level: { label: "GP-level forecast", icon: Database, className: "bg-ash-gray text-graphite" },
  pass_through: { label: "Block forecast (pass-through)", icon: Radio, className: "bg-ash-gray text-graphite" },
}

const CLASSIFICATION_LABELS: Record<MlClassification, { label: string; icon: typeof Cpu; className: string }> = {
  REAL_ML_PREDICTION: { label: "ML Prediction", icon: Cpu, className: "bg-sage-card text-forest-ink" },
  RULE_BASED_LOGIC: { label: "Rule-based", icon: ListChecks, className: "bg-peach-card text-graphite" },
  RAW_DATA_API_VALUE: { label: "Raw data", icon: Database, className: "bg-ash-gray text-graphite" },
  PASS_THROUGH_VALUE: { label: "Pass-through value", icon: Radio, className: "bg-ash-gray text-graphite" },
}

export function MLSourceBadge({ source, classification }: { source?: ValueSource; classification?: MlClassification }) {
  const spec = classification ? CLASSIFICATION_LABELS[classification] : source ? SOURCE_LABELS[source] : null
  if (!spec) return null
  const Icon = spec.icon

  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", spec.className)}>
      <Icon className="size-3" aria-hidden="true" />
      {spec.label}
    </span>
  )
}
