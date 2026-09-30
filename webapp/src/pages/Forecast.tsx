import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { useNavigate } from "react-router-dom"

import { AdvisoryCard } from "@/components/AdvisoryCard"
import { DailyForecastCard } from "@/components/DailyForecastCard"
import { EmptyState } from "@/components/EmptyState"
import { ErrorState } from "@/components/ErrorState"
import { HourlyForecast } from "@/components/HourlyForecast"
import { LoadingState } from "@/components/LoadingState"
import { PanchayatForecastMap } from "@/components/PanchayatForecastMap"
import { RiskLevelCard } from "@/components/RiskLevelCard"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TodayOutlookCharts } from "@/components/TodayOutlookCharts"
import { WeatherAlert } from "@/components/WeatherAlert"
import { WeatherCard } from "@/components/WeatherCard"
import {
  buildAdvisoryDetail,
  computeForecastRiskForRow,
  computeRainfallOutlook,
} from "@/lib/advisory"
import {
  getAlertsForGp,
  getForecast,
  getForecastForGp,
  getHourlyEstimated,
  type ForecastRow,
} from "@/lib/api"
import { useAuth } from "@/lib/AuthProvider"
import { useKhammamMandalsGeoJson } from "@/lib/useKhammamMandalsGeoJson"
import { useSelectedGp } from "@/lib/useSelectedGp"

const CONFIDENCE_NOTE: Record<string, string> = {
  high: "This Panchayat is closer than most to the nearest weather grid cell -- the downscaling method is more reliable here.",
  medium: "This Panchayat is farther from the nearest weather grid cell -- treat the downscaled value as a rougher estimate.",
}

export function Forecast() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { gps, selectedGp, selectGp } = useSelectedGp()
  const [selectedDate, setSelectedDate] = useState("")

  const forecastQuery = useQuery({
    queryKey: ["forecast", selectedGp],
    queryFn: () => getForecastForGp(selectedGp),
    enabled: !!selectedGp,
  })
  const allForecastQuery = useQuery({ queryKey: ["forecast-all"], queryFn: getForecast })
  const alertsQuery = useQuery({
    queryKey: ["alerts", selectedGp],
    queryFn: () => getAlertsForGp(selectedGp),
    enabled: !!selectedGp,
  })
  const mandalsQuery = useKhammamMandalsGeoJson()

  const rows = forecastQuery.data ?? []
  const activeDate = rows.some((r) => r.date === selectedDate) ? selectedDate : (rows[0]?.date ?? "")
  const hourlyQuery = useQuery({
    queryKey: ["hourly", selectedGp, activeDate],
    queryFn: () => getHourlyEstimated(selectedGp, activeDate),
    enabled: !!selectedGp && !!activeDate,
  })

  if (!user?.selected_district || !user?.selected_block) {
    return (
      <EmptyState
        message="Set your location on Home first -- the Panchayat forecast needs a selected State/District/Block."
        actionLabel="Go to Home"
        onAction={() => navigate("/dashboard")}
      />
    )
  }

  if (!selectedGp || forecastQuery.isLoading || allForecastQuery.isLoading || mandalsQuery.isLoading) {
    return <LoadingState label="Loading Panchayat forecast..." />
  }
  if (forecastQuery.isError || rows.length === 0) {
    return <ErrorState message="Unable to load the forecast for this Panchayat." onRetry={() => forecastQuery.refetch()} />
  }

  const activeRow: ForecastRow = rows.find((r) => r.date === activeDate) ?? rows[0]
  const blockFeature = mandalsQuery.data?.features.find((f) => f.properties.mandal === user.selected_block) ?? null

  const rowsByGpAndDate = new Map<string, Map<string, ForecastRow>>()
  for (const r of allForecastQuery.data ?? []) {
    if (!rowsByGpAndDate.has(r.gram_panchayat)) rowsByGpAndDate.set(r.gram_panchayat, new Map())
    rowsByGpAndDate.get(r.gram_panchayat)!.set(r.date, r)
  }

  const advisory = buildAdvisoryDetail(activeRow)
  const riskBreakdown = computeForecastRiskForRow(activeRow)
  const rainfallOutlook = computeRainfallOutlook(rows)

  const comparisonRows = (allForecastQuery.data ?? [])
    .filter((r) => r.date === activeDate && r.rainfall_mm != null)
    .sort((a, b) => (b.rainfall_mm ?? 0) - (a.rainfall_mm ?? 0))
  const maxComparisonRainfall = Math.max(1, ...comparisonRows.map((r) => r.rainfall_mm ?? 0))

  return (
    <div className="space-y-6">
      {/* 1. Location context */}
      <div>
        <h1 className="font-serif text-2xl font-medium text-charcoal">Forecast</h1>
        <p className="mt-1 text-sm text-graphite">
          📍 {user.selected_state} → {user.selected_district} → {user.selected_block}
        </p>
      </div>

      {/* 2-3. Block-level Panchayat map */}
      <div className="rounded-card bg-card p-6">
        <h2 className="mb-1 font-serif text-lg font-medium text-charcoal">Panchayat Forecast Map</h2>
        <p className="mb-4 text-sm text-graphite">Block: {user.selected_block}</p>
        <PanchayatForecastMap
          block={user.selected_block}
          blockFeature={blockFeature as unknown as GeoJSON.Feature | null}
          gps={gps}
          rowsByGpAndDate={rowsByGpAndDate}
          dates={rows.map((r) => r.date)}
          selectedGp={selectedGp}
          onSelectGp={selectGp}
        />
      </div>

      {/* 5B. Panchayat selector */}
      <div className="flex flex-wrap items-center gap-3 rounded-card bg-card p-4">
        <label className="text-sm font-medium text-charcoal">Select Panchayat to view detailed forecast</label>
        <Select value={selectedGp} onValueChange={(gp) => gp && selectGp(gp)}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Select Panchayat" />
          </SelectTrigger>
          <SelectContent>
            {[...gps]
              .sort((a, b) => a.gram_panchayat.localeCompare(b.gram_panchayat))
              .map((gp) => (
                <SelectItem key={gp.gram_panchayat} value={gp.gram_panchayat}>
                  {gp.gram_panchayat}
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </div>

      {/* 6. Selected Panchayat summary */}
      <div className="space-y-2">
        <p className="text-xs text-graphite">
          {selectedGp} Panchayat · Block: {user.selected_block} · District: {user.selected_district}
        </p>
        <WeatherCard row={activeRow} />
        <div className="flex items-center gap-2 text-xs text-graphite">
          <span className="font-medium text-charcoal">Forecast Confidence:</span>
          <span className={activeRow.confidence === "high" ? "text-status-safe" : "text-status-warning"}>
            {activeRow.confidence.toUpperCase()}
          </span>
        </div>
        <p className="text-xs italic text-pewter">{CONFIDENCE_NOTE[activeRow.confidence]}</p>
      </div>

      {/* 7-8. 5-day forecast (this project's real forecast horizon is 5
       * days -- see README/docs/FOUNDATION.md; never padded to look like 7). */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">5-Day Forecast</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {rows.map((row, i) => (
            <DailyForecastCard
              key={row.date}
              row={row}
              isFirst={i === 0}
              selected={row.date === activeDate}
              onSelect={() => setSelectedDate(row.date)}
            />
          ))}
        </div>
      </div>

      {/* 9. Hourly forecast for the selected day */}
      {hourlyQuery.data && (
        <HourlyForecast points={hourlyQuery.data.points} />
      )}

      {/* 10. Weather trend graphs (reused from Home) */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">Weather Trends</h2>
        <TodayOutlookCharts rows={rows} />
      </div>

      {/* 11-12. Rainfall outlook */}
      <div className="rounded-card bg-card p-6">
        <h2 className="mb-4 font-serif text-lg font-medium text-charcoal">🌧 Rainfall Outlook</h2>
        {rainfallOutlook ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-xs text-pewter">Expected rainfall</p>
              <p className="text-lg font-medium text-charcoal">{rainfallOutlook.total_mm}mm</p>
            </div>
            <div>
              <p className="text-xs text-pewter">Rainy days</p>
              <p className="text-lg font-medium text-charcoal">
                {rainfallOutlook.rainy_days} / {rainfallOutlook.total_days}
              </p>
            </div>
            <div>
              <p className="text-xs text-pewter">Highest expected rainfall</p>
              <p className="text-lg font-medium text-charcoal">{rainfallOutlook.highest_day?.mm.toFixed(1)}mm</p>
            </div>
            <div>
              <p className="text-xs text-pewter">Highest rainfall day</p>
              <p className="text-lg font-medium text-charcoal">
                {rainfallOutlook.highest_day &&
                  new Date(rainfallOutlook.highest_day.date).toLocaleDateString(undefined, { weekday: "long" })}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm italic text-pewter">Data unavailable.</p>
        )}
        <p className="mt-3 text-xs italic text-pewter">
          Rain probability is not shown -- no probability field exists in this forecast pipeline; only real
          computed totals are shown above.
        </p>
      </div>

      {/* 13. Weather risk (rule-based, never labeled ML) */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">Weather Risk -- {new Date(activeRow.date).toLocaleDateString(undefined, { weekday: "long" })}</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <RiskLevelCard
            title="🌡 Heat Risk"
            level={riskBreakdown.heat_risk.level === "UNKNOWN" ? null : riskBreakdown.heat_risk.level}
            why={`${riskBreakdown.heat_risk.label} (Derived forecast risk, not ML).`}
            classification="RULE_BASED_LOGIC"
          />
          <RiskLevelCard
            title="🌧 Heavy Rain Risk"
            level={riskBreakdown.heavy_rain_risk.level === "UNKNOWN" ? null : riskBreakdown.heavy_rain_risk.level}
            why={`${riskBreakdown.heavy_rain_risk.label} (Derived forecast risk, not ML).`}
            classification="RULE_BASED_LOGIC"
          />
          <RiskLevelCard
            title="💧 Excess Humidity"
            level={riskBreakdown.humidity_risk.level === "UNKNOWN" ? null : riskBreakdown.humidity_risk.level}
            why={`${riskBreakdown.humidity_risk.label} (Derived forecast risk, not ML).`}
            classification="RULE_BASED_LOGIC"
          />
          <RiskLevelCard
            title="💨 Strong Wind Risk"
            level={null}
            why={riskBreakdown.wind_risk.label}
            unavailableReason={riskBreakdown.wind_risk.label}
          />
        </div>
      </div>

      {/* 14. Warnings */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">⚠️ Warnings</h2>
        {(alertsQuery.data ?? []).length === 0 ? (
          <div className="rounded-card bg-status-safe-bg p-4 text-sm font-medium text-status-safe">
            ✓ No major weather warnings for {selectedGp}.
          </div>
        ) : (
          <div className="space-y-3">
            {(alertsQuery.data ?? []).map((a) => (
              <WeatherAlert
                key={`${a.gram_panchayat}-${a.date}`}
                severity={a.severity}
                title={a.title}
                description={a.description}
                action={a.action}
                dateLabel={new Date(a.date).toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}
              />
            ))}
          </div>
        )}
      </div>

      {/* 16. Uncertainty / prediction range -- not fabricated: this model
       * produces point predictions only (see models/training_report.md),
       * no prediction interval. Structured so it can be filled in later. */}
      <div className="rounded-card bg-ash-gray/50 p-5 text-sm text-graphite">
        <p className="font-medium text-charcoal">Prediction Range</p>
        <p className="mt-1 italic text-pewter">
          Not available -- the trained rainfall model produces a single point prediction, not a prediction interval.
        </p>
      </div>

      {/* 17. Panchayat comparison for the active date */}
      {comparisonRows.length > 1 && (
        <div className="rounded-card bg-card p-6">
          <h2 className="mb-1 font-serif text-lg font-medium text-charcoal">Panchayat Rainfall Outlook</h2>
          <p className="mb-4 text-xs text-pewter">
            {new Date(activeDate).toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })} · real per-Panchayat downscaled values
          </p>
          <div className="space-y-2">
            {comparisonRows.map((r) => (
              <div key={r.gram_panchayat} className="flex items-center gap-3 text-sm">
                <span className={r.gram_panchayat === selectedGp ? "w-28 shrink-0 font-medium text-forest-ink" : "w-28 shrink-0 text-graphite"}>
                  {r.gram_panchayat}
                </span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-ash-gray">
                  <div
                    className={r.gram_panchayat === selectedGp ? "h-full rounded-full bg-forest-ink" : "h-full rounded-full bg-status-info"}
                    style={{ width: `${((r.rainfall_mm ?? 0) / maxComparisonRainfall) * 100}%` }}
                  />
                </div>
                <span className="w-16 shrink-0 text-right text-graphite">{(r.rainfall_mm ?? 0).toFixed(1)}mm</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 20-21. Agricultural impact + forecast advisory -- reuses the same
       * AdvisoryCard/buildAdvisoryDetail already used on Home, applied to
       * the selected day rather than only "today". Not a second engine. */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🤖 Forecast Advisory</h2>
        <AdvisoryCard
          {...advisory}
          gramPanchayat={selectedGp}
          dateLabel={new Date(activeRow.date).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
          prominent
        />
      </div>
    </div>
  )
}
