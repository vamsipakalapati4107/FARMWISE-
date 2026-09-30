import { useQuery } from "@tanstack/react-query"
import { Link, useNavigate } from "react-router-dom"

import { CropHealthSection } from "@/components/CropHealthSection"
import { EmptyState } from "@/components/EmptyState"
import { ErrorState } from "@/components/ErrorState"
import { LoadingState } from "@/components/LoadingState"
import { MLSourceBadge } from "@/components/MLSourceBadge"
import { RecommendationCard } from "@/components/RecommendationCard"
import { RiskLevelCard } from "@/components/RiskLevelCard"
import { WeatherAlert } from "@/components/WeatherAlert"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { classifyForecastRow, fieldInspectionDecision } from "@/lib/advisory"
import {
  getCropHealth,
  getFarmAdvisor,
  getPlot,
  getPlotAlerts,
  getPlotAnalytics,
  getPlotWeather,
} from "@/lib/api"
import { useSelectedPlot } from "@/lib/useSelectedPlot"

const STATUS_META: Record<string, { label: string; text: string; bg: string }> = {
  avoid: { label: "Avoid", text: "text-status-critical", bg: "bg-status-critical-bg" },
  delay: { label: "Delay", text: "text-status-warning", bg: "bg-status-warning-bg" },
  recommended: { label: "Recommended", text: "text-status-info", bg: "bg-status-info-bg" },
  monitor: { label: "Monitor", text: "text-status-warning", bg: "bg-status-warning-bg" },
  normal: { label: "Normal", text: "text-status-safe", bg: "bg-status-safe-bg" },
}

export function Advisory() {
  const navigate = useNavigate()
  const { farms, plots, selectedPlotId, selectPlot, isLoading: plotsLoading } = useSelectedPlot()

  const plotQuery = useQuery({ queryKey: ["plot", selectedPlotId], queryFn: () => getPlot(selectedPlotId), enabled: !!selectedPlotId })
  const weatherQuery = useQuery({
    queryKey: ["plot-weather", selectedPlotId],
    queryFn: () => getPlotWeather(selectedPlotId),
    enabled: !!selectedPlotId,
  })
  const advisorQuery = useQuery({
    queryKey: ["farm-advisor", selectedPlotId],
    queryFn: () => getFarmAdvisor(selectedPlotId),
    enabled: !!selectedPlotId,
  })
  const healthQuery = useQuery({
    queryKey: ["crop-health", selectedPlotId],
    queryFn: () => getCropHealth(selectedPlotId),
    enabled: !!selectedPlotId,
  })
  const alertsQuery = useQuery({
    queryKey: ["plot-alerts", selectedPlotId],
    queryFn: () => getPlotAlerts(selectedPlotId),
    enabled: !!selectedPlotId,
  })
  const analyticsQuery = useQuery({
    queryKey: ["plot-analytics", selectedPlotId],
    queryFn: () => getPlotAnalytics(selectedPlotId, 7),
    enabled: !!selectedPlotId,
  })

  if (plotsLoading) return <LoadingState label="Loading your farm..." />

  if (farms.length === 0) {
    return (
      <EmptyState
        message="Add a farm to get farm-specific advisory, not just weather."
        actionLabel="Add Farm"
        onAction={() => navigate("/farm")}
      />
    )
  }
  if (plots.length === 0) {
    return (
      <EmptyState
        message="Advisory needs a Plot to give field-level decisions (crop health, disease risk, field inspection). Add a plot to one of your farms in My Farm."
        actionLabel="Go to My Farm"
        onAction={() => navigate("/farm")}
      />
    )
  }
  if (!selectedPlotId || advisorQuery.isLoading || healthQuery.isLoading || weatherQuery.isLoading) {
    return <LoadingState label="Loading advisory..." />
  }
  if (advisorQuery.isError || !advisorQuery.data) {
    return <ErrorState message="Prediction unavailable -- could not load the farm advisor for this plot." onRetry={() => advisorQuery.refetch()} />
  }

  const advisor = advisorQuery.data
  const plot = plotQuery.data
  const weather = weatherQuery.data
  const selectedPlot = plots.find((p) => p.id === selectedPlotId)
  const activeAlerts = (alertsQuery.data ?? []).filter((a) => a.status !== "resolved" && a.status !== "expired")
  const analytics = analyticsQuery.data

  const actionableRecs = advisor.recommendations.filter((r) => r.status !== "normal")
  const inspection = fieldInspectionDecision(advisor)

  // Precautions Center: consolidate the same recommendations, one line each.
  const precautionIcons: Record<string, string> = {
    irrigation: "💧",
    fertilizer: "🧪",
    disease_monitoring: "🦠",
    field_inspection: "🔎",
    weather_precautions: "🌦",
    general_operations: "🚜",
  }

  // 5-Day Farm Action Plan -- real forecast days, never padded to 7.
  const actionCalendar = (analytics?.forecast ?? []).map((day, i) => {
    const { severity, label } = classifyForecastRow({
      rainfall_mm: day.rainfall_mm,
      temp_max_c: day.temp_max_c,
      rh_max_pct: day.rh_max_pct,
    })
    const items: string[] = []
    if (severity === "critical" && label === "Heavy rain") items.push("🌧 Rain expected -- reassess irrigation & drainage")
    if (severity === "critical" && label === "Heat stress") items.push("🌡 High heat expected -- avoid midday fieldwork")
    if (label === "Fungal disease risk") items.push("🦠 Continue disease monitoring")
    if (i === 0 && inspection && inspection.decision !== "MONITOR") items.push("🔎 Field inspection")
    return { date: day.date, items, isFirst: i === 0 }
  })

  return (
    <div className="space-y-6">
      {/* 1. Location / Farm / Plot / Crop context */}
      <div>
        <h1 className="font-serif text-2xl font-medium text-charcoal">Advisory</h1>
        {plot && (
          <p className="mt-1 text-sm text-graphite">
            📍 {plot.name} · {selectedPlot?.farm_name}
            {advisor.crop ? ` · 🌱 ${advisor.crop.crop_name}${advisor.crop.variety ? ` (${advisor.crop.variety})` : ""} · 🌿 ${advisor.crop.stage}` : " · 🌱 No crop recorded"}
          </p>
        )}
      </div>

      {plots.length > 1 && (
        <div className="flex flex-wrap items-center gap-3 rounded-card bg-card p-4">
          <label className="text-sm font-medium text-charcoal">Plot</label>
          <Select value={selectedPlotId} onValueChange={(id) => id && selectPlot(id)}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Select plot" />
            </SelectTrigger>
            <SelectContent>
              {plots.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name} ({p.farm_name})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* 2. Current farm situation */}
      {weather && (
        <div className="rounded-card bg-card p-6">
          <h2 className="mb-4 font-serif text-lg font-medium text-charcoal">📋 Current Farm Situation</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {(
              [
                ["🌡 Temperature", weather.temp_max_c, "°C"],
                ["🌧 Rainfall", weather.rainfall_mm, "mm"],
                ["💧 Humidity", weather.rh_max_pct, "%"],
                ["💨 Wind", weather.wind_max_kmh, "km/h"],
              ] as const
            ).map(([label, field, unit]) => (
              <div key={label}>
                <p className="text-xs text-pewter">{label}</p>
                <p className="text-sm font-medium text-charcoal">
                  {field.value != null ? `${Math.round(field.value * 10) / 10}${unit}` : "Data unavailable"}
                </p>
                <MLSourceBadge source={field.source} />
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs italic text-pewter">💧 Soil Moisture: Data unavailable -- no soil sensor/data source exists in this project.</p>
        </div>
      )}

      {/* 3. Today's decision summary */}
      <div className={actionableRecs.length > 0 ? "rounded-card border-l-4 border-status-warning bg-status-warning-bg p-5" : "rounded-card bg-status-safe-bg p-5"}>
        <p className="font-serif text-lg font-medium text-charcoal">
          {actionableRecs.length > 0 ? `🚨 ${actionableRecs.length} Action${actionableRecs.length > 1 ? "s" : ""} Recommended` : "🟢 No urgent actions today"}
        </p>
        {actionableRecs.length > 0 && (
          <ol className="mt-2 space-y-1 text-sm text-charcoal">
            {advisor.action_plan.map((item) => (
              <li key={item.category}>
                {item.priority}. {precautionIcons[item.category]} {item.label}
              </li>
            ))}
          </ol>
        )}
      </div>

      {/* 4. Field inspection decision */}
      {inspection && (
        <div className="rounded-card bg-card p-6">
          <h2 className="mb-2 font-serif text-lg font-medium text-charcoal">🔎 Field Inspection Required</h2>
          <p className="text-xl font-medium text-forest-ink">{inspection.decision}</p>
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="font-medium text-charcoal">Reason</dt>
              <dd className="text-graphite">{inspection.why}</dd>
            </div>
            <div>
              <dt className="font-medium text-charcoal">Priority</dt>
              <dd className="text-graphite">{inspection.priority}</dd>
            </div>
            <div>
              <dt className="font-medium text-charcoal">Recommended time</dt>
              <dd className="text-graphite">{inspection.when}</dd>
            </div>
          </dl>
          {inspection.decision !== "MONITOR" && (
            <div className="mt-4">
              <p className="mb-1.5 text-sm font-medium text-charcoal">What to inspect</p>
              <ul className="ml-4 list-disc space-y-1 text-sm text-graphite">
                {inspection.points.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs italic text-pewter">
                Monitor for these signs -- this indicates elevated risk, not a confirmed diagnosis.
              </p>
            </div>
          )}
        </div>
      )}

      {/* 6. AI Crop Health Advisor (reused component, not rebuilt) */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🤖 AI Crop Health Advisor</h2>
        {healthQuery.data ? <CropHealthSection data={healthQuery.data} /> : <EmptyState message="Crop health unavailable." />}
      </div>

      {/* 8. Disease & pest advisory */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🦠 Disease &amp; Pest Risk</h2>
        <RiskLevelCard
          title="Disease Risk"
          level={advisor.disease_risk.level}
          why={advisor.disease_risk.why}
          classification={advisor.disease_risk.classification}
        />
      </div>

      {/* 9. Weather risk advisory (real forecast-derived risk, 5-day window) */}
      {analytics?.forecast_risk && (
        <div>
          <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🌦 Weather Risk</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <RiskLevelCard
              title="🌡 Heat Risk"
              level={analytics.forecast_risk.heat_risk.level === "UNKNOWN" ? null : (analytics.forecast_risk.heat_risk.level as "LOW" | "MEDIUM" | "HIGH")}
              why={analytics.forecast_risk.heat_risk.label}
              classification="RULE_BASED_LOGIC"
            />
            <RiskLevelCard
              title="🌧 Heavy Rain Risk"
              level={analytics.forecast_risk.heavy_rain_risk.level === "UNKNOWN" ? null : (analytics.forecast_risk.heavy_rain_risk.level as "LOW" | "MEDIUM" | "HIGH")}
              why={analytics.forecast_risk.heavy_rain_risk.label}
              classification="RULE_BASED_LOGIC"
            />
            <RiskLevelCard
              title="💧 Excess Humidity"
              level={analytics.forecast_risk.humidity_risk.level === "UNKNOWN" ? null : (analytics.forecast_risk.humidity_risk.level as "LOW" | "MEDIUM" | "HIGH")}
              why={analytics.forecast_risk.humidity_risk.label}
              classification="RULE_BASED_LOGIC"
            />
            <RiskLevelCard title="💨 Wind Risk" level={null} why={analytics.forecast_risk.wind_risk.label} unavailableReason={analytics.forecast_risk.wind_risk.label} />
          </div>
        </div>
      )}

      {/* 10. Irrigation advisory */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">💧 Irrigation Advisory</h2>
        {(() => {
          const rec = advisor.recommendations.find((r) => r.category === "irrigation")
          return rec ? <RecommendationCard recommendation={rec} /> : <EmptyState message="Insufficient data." />
        })()}
      </div>

      {/* 11. Nutrient / fertilizer advisory */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🧪 Nutrient / Fertilizer</h2>
        {(() => {
          const rec = advisor.recommendations.find((r) => r.category === "fertilizer")
          return rec ? (
            <RecommendationCard recommendation={rec} />
          ) : (
            <EmptyState message="Specific nutrient recommendation unavailable without soil information." />
          )
        })()}
      </div>

      {/* 12. Farm operations -- remaining categories */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🚜 Field Operations</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {advisor.recommendations
            .filter((r) => !["irrigation", "fertilizer"].includes(r.category))
            .map((r) => (
              <RecommendationCard key={r.category} recommendation={r} />
            ))}
        </div>
        <p className="mt-2 text-xs italic text-pewter">
          Sowing/harvesting/weeding suitability aren't modeled separately in this system -- these 6 categories
          (irrigation, fertilizer, disease monitoring, field inspection, weather precautions, general operations)
          are the real rule-based coverage that exists.
        </p>
      </div>

      {/* 13. Precautions center */}
      <div className="rounded-card bg-card p-6">
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🛡️ Today's Precautions</h2>
        {actionableRecs.length === 0 ? (
          <p className="text-sm text-status-safe">✓ No elevated risks -- no special precautions today.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {actionableRecs.map((r) => (
              <li key={r.category} className="flex items-start gap-2">
                <span>{precautionIcons[r.category]}</span>
                <span className="text-charcoal">
                  <span className={STATUS_META[r.status].text + " font-medium"}>{STATUS_META[r.status].label}:</span> {r.what}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 14. 5-day farm action calendar (real forecast horizon, not padded to 7) */}
      {actionCalendar.length > 0 && (
        <div>
          <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">📅 5-Day Farm Action Plan</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {actionCalendar.map((day) => (
              <div key={day.date} className="rounded-card bg-card p-4 text-sm">
                <p className="font-medium text-charcoal">
                  {day.isFirst ? "TODAY" : new Date(day.date).toLocaleDateString(undefined, { weekday: "short" }).toUpperCase()}
                </p>
                <p className="mb-2 text-xs text-pewter">{new Date(day.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</p>
                {day.items.length === 0 ? (
                  <p className="text-xs text-status-safe">✓ Routine monitoring</p>
                ) : (
                  <ul className="space-y-1 text-xs text-graphite">
                    {day.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alerts connection (reused, not a second engine) */}
      {activeAlerts.length > 0 && (
        <div>
          <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">⚠️ Active Alerts for This Plot</h2>
          <div className="space-y-3">
            {activeAlerts.map((a) => (
              <WeatherAlert
                key={a.id}
                severity={a.severity === "attention" ? "warning" : a.severity === "info" ? "safe" : a.severity}
                title={a.title}
                description={a.reason}
                action={a.recommended_action}
                dateLabel={new Date(a.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              />
            ))}
          </div>
        </div>
      )}

      {/* 16/17. ML / data reasoning + explainable "why" -- reused technical
       * details already computed server-side, not re-derived. */}
      <div className="rounded-card bg-ash-gray/50 p-5 text-sm text-graphite">
        <p className="mb-2 font-medium text-charcoal">🤖 ML / Data Reasoning -- Why am I seeing this?</p>
        <ul className="ml-4 list-disc space-y-1">
          {Object.entries(advisor.technical_details.data_used).map(([key, field]) => (
            <li key={key}>
              {key}: {field.value ?? "N/A"} ({field.source})
            </li>
          ))}
        </ul>
        <p className="mt-3">
          <span className="font-medium text-charcoal">Model:</span> {advisor.technical_details.ml_prediction_used.model_name} (
          {advisor.technical_details.ml_prediction_used.classification}) -- GP-level value:{" "}
          {advisor.technical_details.ml_prediction_used.gp_level_value ?? "N/A"}
        </p>
        <p className="mt-1 text-xs italic text-pewter">
          No probability/confidence percentage is reported here -- the underlying rule/model output doesn't produce
          one (see docs/FOUNDATION.md); showing a number would be invented, not real.
        </p>
        {advisor.technical_details.rules_triggered.length > 0 && (
          <>
            <p className="mt-3 font-medium text-charcoal">Rules triggered</p>
            <ul className="ml-4 list-disc">
              {advisor.technical_details.rules_triggered.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </>
        )}
        {analytics?.insights && analytics.insights.length > 0 && (
          <>
            <p className="mt-3 font-medium text-charcoal">Supporting evidence</p>
            <ul className="ml-4 list-disc">
              {analytics.insights.map((insight, i) => (
                <li key={i}>{insight.text}</li>
              ))}
            </ul>
          </>
        )}
        <p className="mt-3 text-xs text-pewter">Generated: {new Date(advisor.technical_details.timestamp).toLocaleString()}</p>
      </div>

      <p className="text-center text-xs text-pewter">
        <Link to={`/plots/${selectedPlotId}`} className="text-forest-ink hover:underline">
          View full Plot Detail →
        </Link>
      </p>
    </div>
  )
}
