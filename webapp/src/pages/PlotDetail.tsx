import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, MapPin, MapPinOff, Sparkles } from "lucide-react"
import { Link, useParams } from "react-router-dom"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { CATEGORY_META } from "@/components/RecommendationCard"
import { RecommendationCard } from "@/components/RecommendationCard"
import { RiskLevelCard } from "@/components/RiskLevelCard"
import { CropHealthSection } from "@/components/CropHealthSection"
import { ErrorState } from "@/components/ErrorState"
import { LoadingState } from "@/components/LoadingState"
import { getCropHealth, getFarmAdvisor, getPlot, getPlotAlerts, type AlertSeverity4 } from "@/lib/api"
import { cn } from "@/lib/utils"

const STATUS_ICON_TONE: Record<string, string> = {
  avoid: "text-status-critical",
  delay: "text-status-warning",
  recommended: "text-status-info",
  monitor: "text-status-warning",
}

const ALERT_EMOJI: Record<AlertSeverity4, string> = {
  critical: "\u{1F534}",
  warning: "\u{1F7E0}",
  attention: "\u{1F7E1}",
  info: "\u{1F7E2}",
}

export function PlotDetail() {
  const { plotId = "" } = useParams<{ plotId: string }>()

  const plotQuery = useQuery({ queryKey: ["plot", plotId], queryFn: () => getPlot(plotId), enabled: !!plotId })
  const advisorQuery = useQuery({
    queryKey: ["farm-advisor", plotId],
    queryFn: () => getFarmAdvisor(plotId),
    enabled: !!plotId,
  })
  const healthQuery = useQuery({
    queryKey: ["crop-health", plotId],
    queryFn: () => getCropHealth(plotId),
    enabled: !!plotId,
  })
  const plotAlertsQuery = useQuery({
    queryKey: ["plot-alerts", plotId],
    queryFn: () => getPlotAlerts(plotId),
    enabled: !!plotId,
  })

  if (plotQuery.isLoading || advisorQuery.isLoading) return <LoadingState />
  if (plotQuery.isError || !plotQuery.data) return <ErrorState message="Plot not found." />
  if (advisorQuery.isError || !advisorQuery.data) {
    return <ErrorState message="Prediction unavailable -- could not load the farm advisor for this plot." onRetry={() => advisorQuery.refetch()} />
  }

  const plot = plotQuery.data
  const advisor = advisorQuery.data
  const hasCoordinates = plot.latitude != null && plot.longitude != null

  return (
    <div className="space-y-6">
      <Link to="/farm" className="inline-flex items-center gap-1.5 text-sm text-forest-ink hover:underline">
        <ArrowLeft className="size-4" /> Back to My Farm
      </Link>

      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-serif text-2xl font-medium text-charcoal">{plot.name}</h1>
          <div className="mt-1 flex items-center gap-1.5 text-sm text-graphite">
            {hasCoordinates ? (
              <>
                <MapPin className="size-4 text-status-safe" />
                {plot.latitude!.toFixed(4)}, {plot.longitude!.toFixed(4)}
              </>
            ) : (
              <>
                <MapPinOff className="size-4 text-status-warning" />
                <span className="italic">Location not configured -- showing Gram Panchayat-level weather</span>
              </>
            )}
          </div>
        </div>
        <Link
          to={`/plots/${plotId}/analytics`}
          className="whitespace-nowrap rounded-nav-pill bg-forest-ink px-4 py-2 text-sm font-medium text-white hover:bg-forest-ink/90"
        >
          📊 Analytics
        </Link>
      </div>

      {(plotAlertsQuery.data ?? []).filter((a) => a.status !== "resolved" && a.status !== "expired").length > 0 && (
        <div>
          <h2 className="mb-3 font-serif text-xl font-medium text-charcoal">Active Alerts</h2>
          <div className="flex flex-wrap gap-2">
            {(plotAlertsQuery.data ?? [])
              .filter((a) => a.status !== "resolved" && a.status !== "expired")
              .map((a) => (
                <Link
                  key={a.id}
                  to="/alerts"
                  className="rounded-nav-pill bg-card px-3 py-1.5 text-sm text-charcoal ring-1 ring-moss hover:bg-ash-gray/60"
                  title={`${a.reason} — ${a.recommended_action}`}
                >
                  {ALERT_EMOJI[a.severity]} {a.title}
                </Link>
              ))}
          </div>
        </div>
      )}

      <div>
        <h2 className="mb-3 font-serif text-xl font-medium text-charcoal">Crop Health &amp; Stress Intelligence</h2>
        {healthQuery.isLoading ? (
          <LoadingState label="Loading crop health..." />
        ) : healthQuery.isError || !healthQuery.data ? (
          <ErrorState message="Insufficient data for this recommendation." onRetry={() => healthQuery.refetch()} />
        ) : (
          <CropHealthSection data={healthQuery.data} />
        )}
      </div>

      <div className="rounded-card bg-forest-ink p-5 text-white">
        <div className="flex items-center gap-2">
          <Sparkles className="size-5 text-vivid-lime" aria-hidden="true" />
          <h2 className="font-serif text-xl font-medium">AI Farm Advisor</h2>
        </div>
        <p className="mt-1 text-sm text-white/80">What should I do today? · {advisor.date}</p>
        {advisor.crop && (
          <p className="mt-1 text-sm text-white/70">
            {advisor.crop.crop_name}
            {advisor.crop.variety && ` (${advisor.crop.variety})`} · {advisor.crop.stage} stage
          </p>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-medium text-graphite">Today's Farm Status</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <RiskLevelCard
            title="Disease Risk"
            level={advisor.disease_risk.level}
            why={advisor.disease_risk.why}
            classification={advisor.disease_risk.classification}
          />
          <RiskLevelCard
            title="Weather Risk"
            level={advisor.weather_risk.level}
            why={advisor.weather_risk.why}
            classification={advisor.weather_risk.classification}
          />
          <RiskLevelCard
            title="Crop Condition"
            level={null}
            why={advisor.crop_condition.reason}
            unavailableReason={advisor.crop_condition.reason}
          />
        </div>
      </div>

      {advisor.action_plan.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-medium text-graphite">Today's Action Plan</h2>
          <div className="rounded-card bg-card p-5">
            <ol className="space-y-3">
              {advisor.action_plan.map((item) => {
                const { label, icon: Icon } = CATEGORY_META[item.category]
                return (
                  <li key={item.category} className="flex items-center gap-3 text-sm">
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-sage-card text-xs font-medium text-forest-ink">
                      {item.priority}
                    </span>
                    <Icon className={cn("size-4 shrink-0", STATUS_ICON_TONE[item.status])} aria-hidden="true" />
                    <span className="text-charcoal">
                      <span className="font-medium">{label}:</span> {item.label}
                    </span>
                  </li>
                )
              })}
            </ol>
          </div>
        </div>
      )}

      <div>
        <h2 className="mb-3 text-sm font-medium text-graphite">Detailed Recommendations</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {advisor.recommendations.map((rec) => (
            <RecommendationCard key={rec.category} recommendation={rec} />
          ))}
        </div>
      </div>

      <Accordion>
        <AccordionItem value="technical-details">
          <AccordionTrigger className="text-sm font-medium text-graphite">View Technical Details</AccordionTrigger>
          <AccordionContent>
            <div className="space-y-3 text-sm text-graphite">
              <div>
                <p className="font-medium text-charcoal">Data used</p>
                <ul className="ml-4 list-disc">
                  {Object.entries(advisor.technical_details.data_used).map(([key, field]) => (
                    <li key={key}>
                      {key}: {field.value ?? "N/A"} ({field.source})
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="font-medium text-charcoal">ML prediction used</p>
                <p>
                  {advisor.technical_details.ml_prediction_used.model_name} ({advisor.technical_details.ml_prediction_used.classification}) --
                  GP-level value: {advisor.technical_details.ml_prediction_used.gp_level_value ?? "N/A"}
                </p>
              </div>
              {advisor.technical_details.spatial_estimation_used && (
                <div>
                  <p className="font-medium text-charcoal">Spatial estimation used</p>
                  <p>
                    {advisor.technical_details.spatial_estimation_used.method} -- estimated value{" "}
                    {advisor.technical_details.spatial_estimation_used.value}
                  </p>
                </div>
              )}
              <div>
                <p className="font-medium text-charcoal">Rules triggered</p>
                {advisor.technical_details.rules_triggered.length > 0 ? (
                  <ul className="ml-4 list-disc">
                    {advisor.technical_details.rules_triggered.map((rule) => (
                      <li key={rule}>{rule}</li>
                    ))}
                  </ul>
                ) : (
                  <p>None -- no threshold crossed today.</p>
                )}
              </div>
              <p className="text-xs text-pewter">Generated: {new Date(advisor.technical_details.timestamp).toLocaleString()}</p>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
