import {
  Bug,
  CloudRain,
  Droplet,
  Droplets,
  Sparkles,
  Sprout,
  Thermometer,
  Wind,
} from "lucide-react"

import { MLSourceBadge } from "@/components/MLSourceBadge"
import type { CropHealthResponse, HealthFactor } from "@/lib/api"
import { cn } from "@/lib/utils"

const FACTOR_ICONS: Record<string, typeof Thermometer> = {
  temperature: Thermometer,
  humidity: Droplets,
  rainfall: CloudRain,
  disease_risk: Bug,
  weather_risk: Wind,
  growth_stage: Sprout,
  soil_moisture: Droplet,
}

const HEALTH_STYLES: Record<string, string> = {
  GOOD: "bg-status-safe-bg text-status-safe",
  FAIR: "bg-status-warning-bg text-status-warning",
  POOR: "bg-status-critical-bg text-status-critical",
}

const STRESS_STYLES: Record<string, string> = {
  LOW: "bg-status-safe-bg text-status-safe",
  MEDIUM: "bg-status-warning-bg text-status-warning",
  HIGH: "bg-status-critical-bg text-status-critical",
}

function FactorCard({ factor }: { factor: HealthFactor }) {
  const Icon = FACTOR_ICONS[factor.key] ?? Thermometer
  return (
    <div className="rounded-card bg-card p-4">
      <div className="flex items-center gap-2 text-sm text-graphite">
        <Icon className="size-4 text-forest-ink" aria-hidden="true" />
        {factor.label}
      </div>
      <p className={cn("mt-1 text-sm font-medium", factor.available ? "text-charcoal" : "italic text-pewter")}>
        {factor.available ? factor.status : "Unknown"}
      </p>
    </div>
  )
}

export function CropHealthSection({ data }: { data: CropHealthResponse }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Crop Health */}
        <div className="rounded-card bg-card p-5">
          <h3 className="mb-2 text-sm font-medium text-graphite">🌾 Crop Health</h3>
          {data.health.available ? (
            <>
              <span className={cn("inline-block rounded-full px-4 py-1.5 text-base font-medium", HEALTH_STYLES[data.health.status!])}>
                {data.health.status}
              </span>
              <p className="mt-2 text-xs uppercase tracking-wide text-pewter">{data.health.label}</p>
              <p className="mt-1 text-xs text-graphite">{data.health.reason}</p>
            </>
          ) : (
            <p className="text-sm italic text-pewter">{data.health.reason}</p>
          )}
          <div className="mt-3">
            <MLSourceBadge classification={data.health.source_type === "ml_prediction" ? "REAL_ML_PREDICTION" : "RULE_BASED_LOGIC"} />
          </div>
        </div>

        {/* Crop Stress */}
        <div className="rounded-card bg-card p-5">
          <h3 className="mb-2 text-sm font-medium text-graphite">🌱 Crop Stress</h3>
          {data.stress.available ? (
            <span className={cn("inline-block rounded-full px-4 py-1.5 text-base font-medium", STRESS_STYLES[data.stress.status!])}>
              {data.stress.status}
            </span>
          ) : (
            <>
              <span className="inline-block rounded-full bg-ash-gray px-4 py-1.5 text-base font-medium text-pewter">
                Unavailable
              </span>
              <p className="mt-2 text-xs text-graphite">{data.stress.reason}</p>
            </>
          )}
        </div>
      </div>

      {/* Why? -- one factor card per signal, including unavailable ones
       * (e.g. soil moisture) shown honestly as "Unknown" rather than omitted. */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-graphite">Why?</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {data.factors.map((f) => (
            <FactorCard key={f.key} factor={f} />
          ))}
        </div>
      </div>

      {/* Health trend -- honest empty state */}
      <div className="rounded-card bg-card p-5">
        <h3 className="mb-2 text-sm font-medium text-graphite">📊 Health Trend</h3>
        <p className="text-sm italic text-pewter">{data.health_trend.reason}</p>
      </div>

      {/* Why this result -- explanation */}
      <div className="rounded-card bg-card p-5">
        <h3 className="mb-2 text-sm font-medium text-graphite">🔍 Why This Result?</h3>
        <p className="text-sm italic text-pewter">{data.explanation.reason}</p>
      </div>

      {/* AI Advisor summary -- reuses Phase 1 output, no duplicated logic */}
      {data.advisor_summary.top_recommendation && (
        <div className="rounded-card border-l-4 border-forest-ink bg-sage-card p-5">
          <div className="mb-1 flex items-center gap-2">
            <Sparkles className="size-4 text-forest-ink" aria-hidden="true" />
            <h3 className="text-sm font-medium text-forest-ink">AI Farm Advisor</h3>
          </div>
          <p className="text-sm text-charcoal">{data.advisor_summary.top_recommendation}</p>
        </div>
      )}

      {/* Technical details */}
      <div className="rounded-card bg-ash-gray/60 p-5 text-xs text-graphite">
        <p className="mb-1 font-medium text-charcoal">Technical Details</p>
        <p>Model: {data.technical_details.model ?? "None (no trained model backs this output)"}</p>
        <p>Source: {data.technical_details.source}</p>
        <p>Features used: {data.technical_details.features_used.join(", ") || "none"}</p>
        <p>Timestamp: {new Date(data.technical_details.timestamp).toLocaleString()}</p>
      </div>
    </div>
  )
}
