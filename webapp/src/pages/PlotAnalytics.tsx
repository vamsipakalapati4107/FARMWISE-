import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Sparkles } from "lucide-react"
import { useState, type ReactNode } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Link, useParams } from "react-router-dom"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { EmptyState } from "@/components/EmptyState"
import { ErrorState } from "@/components/ErrorState"
import { LoadingState } from "@/components/LoadingState"
import { cn } from "@/lib/utils"
import {
  getPlot,
  getPlotAnalytics,
  getPlotsIntelligence,
  type ForecastRiskItem,
} from "@/lib/api"

const RISK_STYLES: Record<string, string> = {
  LOW: "bg-status-safe-bg text-status-safe",
  MEDIUM: "bg-status-warning-bg text-status-warning",
  HIGH: "bg-status-critical-bg text-status-critical",
  UNKNOWN: "bg-ash-gray text-pewter",
}

const RISK_TEXT_COLOR: Record<string, string> = {
  LOW: "text-status-safe",
  MEDIUM: "text-status-warning",
  HIGH: "text-status-critical",
  UNKNOWN: "text-pewter",
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-card bg-card p-5">
      <h3 className="mb-3 text-sm font-medium text-graphite">{title}</h3>
      <div className="h-48">{children}</div>
    </div>
  )
}

function RiskRow({ label, item }: { label: string; item: ForecastRiskItem }) {
  return (
    <div className="flex items-center justify-between border-b border-moss/30 py-2 last:border-0">
      <span className="text-sm text-graphite">{label}</span>
      <div className="flex items-center gap-2">
        <span className={cn("rounded-full px-3 py-1 text-xs font-medium", RISK_STYLES[item.level])}>{item.level}</span>
        <span className="text-xs italic text-pewter">{item.label}</span>
      </div>
    </div>
  )
}

export function PlotAnalytics() {
  const { plotId = "" } = useParams<{ plotId: string }>()
  const [rangeDays, setRangeDays] = useState<7 | 30 | 90>(30)

  const plotQuery = useQuery({ queryKey: ["plot", plotId], queryFn: () => getPlot(plotId), enabled: !!plotId })
  const analyticsQuery = useQuery({
    queryKey: ["plot-analytics", plotId, rangeDays],
    queryFn: () => getPlotAnalytics(plotId, rangeDays),
    enabled: !!plotId,
  })
  const intelligenceQuery = useQuery({ queryKey: ["plots-intelligence"], queryFn: getPlotsIntelligence })

  if (plotQuery.isLoading || analyticsQuery.isLoading) return <LoadingState label="Loading analytics..." />
  if (plotQuery.isError || !plotQuery.data) return <ErrorState message="Plot not found." />
  if (analyticsQuery.isError || !analyticsQuery.data) {
    return (
      <ErrorState
        message="Insufficient data for this recommendation."
        onRetry={() => analyticsQuery.refetch()}
      />
    )
  }

  const plot = plotQuery.data
  const data = analyticsQuery.data
  const siblingPlots = (intelligenceQuery.data ?? []).filter((e) => e.farm_id === plot.farm_id)

  const tempChartData = (data.historical.temperature ?? []).map((t) => ({
    date: new Date(t.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    max: t.max_c,
    min: t.min_c,
  }))
  const rainChartData = (data.historical.rainfall ?? []).map((r) => ({
    date: new Date(r.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    mm: r.mm,
  }))
  const humidityChartData = (data.historical.humidity ?? []).map((h) => ({
    date: new Date(h.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    pct: h.max_pct,
  }))

  return (
    <div className="space-y-6">
      <Link to={`/plots/${plotId}`} className="inline-flex items-center gap-1.5 text-sm text-forest-ink hover:underline">
        <ArrowLeft className="size-4" /> Back to {plot.name}
      </Link>

      {/* Header */}
      <div>
        <h1 className="font-serif text-2xl font-medium text-charcoal">📊 Farm Analytics</h1>
        <p className="mt-1 text-sm text-graphite">
          Plot: {plot.name}
          {data.crop && ` · Crop: ${data.crop.crop_name} (${data.crop.stage})`}
        </p>
        <div className="mt-3 flex gap-2">
          {([7, 30, 90] as const).map((d) => (
            <button
              key={d}
              type="button"
              disabled={!data.available_ranges[String(d)]}
              onClick={() => setRangeDays(d)}
              className={cn(
                "rounded-nav-pill px-4 py-1.5 text-sm font-medium transition-colors",
                rangeDays === d ? "bg-forest-ink text-white" : "bg-ash-gray text-graphite hover:bg-moss/40",
                !data.available_ranges[String(d)] && "cursor-not-allowed opacity-40"
              )}
            >
              {d}D
            </button>
          ))}
        </div>
      </div>

      {/* Weather History */}
      <div>
        <h2 className="mb-3 font-serif text-xl font-medium text-charcoal">🌦️ Weather History</h2>
        {!data.historical.available ? (
          <EmptyState message="Historical weather data is not available for this period." />
        ) : (
          <>
            <p className="mb-3 text-xs text-pewter">
              Real observed data, {data.historical.start_date} to {data.historical.end_date} ({data.historical.range_days} days)
            </p>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <ChartCard title="Temperature Trend">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={tempChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-pewter)" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "var(--color-pewter)" }} axisLine={false} tickLine={false} />
                    <Tooltip />
                    <Line type="monotone" dataKey="max" stroke="var(--color-status-critical)" strokeWidth={2} dot={false} name="Max °C" />
                    <Line type="monotone" dataKey="min" stroke="var(--color-status-info)" strokeWidth={2} dot={false} name="Min °C" />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Rainfall">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={rainChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-pewter)" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "var(--color-pewter)" }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v) => [`${Number(v).toFixed(1)}mm`, "Rainfall"]} />
                    <Bar dataKey="mm" fill="var(--color-status-info)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Humidity">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={humidityChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-pewter)" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "var(--color-pewter)" }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v) => [`${v}%`, "Humidity"]} />
                    <Line type="monotone" dataKey="pct" stroke="var(--color-forest-ink)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            {/* Rainfall analytics summary */}
            {data.rainfall_analytics.available && (
              <div className="mt-4 grid grid-cols-2 gap-3 rounded-card bg-card p-5 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-pewter">Total rainfall</p>
                  <p className="text-lg font-medium text-charcoal">{data.rainfall_analytics.total_mm}mm</p>
                </div>
                <div>
                  <p className="text-xs text-pewter">Average / day</p>
                  <p className="text-lg font-medium text-charcoal">{data.rainfall_analytics.average_mm_per_day}mm</p>
                </div>
                <div>
                  <p className="text-xs text-pewter">Rainy days</p>
                  <p className="text-lg font-medium text-charcoal">{data.rainfall_analytics.rainy_days}</p>
                </div>
                <div>
                  <p className="text-xs text-pewter">Highest day</p>
                  <p className="text-lg font-medium text-charcoal">
                    {data.rainfall_analytics.highest_day?.mm}mm ({data.rainfall_analytics.highest_day?.date})
                  </p>
                </div>
                {data.rainfall_analytics.comparison?.available && (
                  <div className="col-span-2 sm:col-span-4">
                    <p className="text-xs text-pewter">
                      Recent average ({data.rainfall_analytics.comparison.recent_average_mm_per_day}mm/day) vs.{" "}
                      {data.rainfall_analytics.comparison.reference_period}: {data.rainfall_analytics.comparison.reference_average_mm_per_day}mm/day
                    </p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Forecast */}
      <div>
        <h2 className="mb-3 font-serif text-xl font-medium text-charcoal">🔮 Forecast</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {data.forecast.map((day) => (
            <div key={day.date} className="rounded-card bg-card p-4 text-center">
              <p className="text-xs font-medium uppercase text-graphite">
                {new Date(day.date).toLocaleDateString(undefined, { weekday: "short" })}
              </p>
              <p className="mt-1 text-lg">{day.condition === "Rain" ? "🌧️" : day.condition === "Clear" ? "☀️" : "❓"}</p>
              <p className="text-sm font-medium text-charcoal">{day.temp_max_c ?? "N/A"}°C</p>
              <p className="text-xs text-pewter">{day.rh_max_pct ?? "N/A"}% humidity</p>
              <p className="text-xs text-pewter">{day.rainfall_mm ?? "N/A"}mm rain</p>
            </div>
          ))}
        </div>
      </div>

      {/* Forecast Risks */}
      {data.forecast_risk && (
        <div>
          <h2 className="mb-3 font-serif text-xl font-medium text-charcoal">⚠️ Forecast Risks</h2>
          <div className="rounded-card bg-card p-5">
            <RiskRow label="Heavy Rain Risk" item={data.forecast_risk.heavy_rain_risk} />
            <RiskRow label="Heat Risk" item={data.forecast_risk.heat_risk} />
            <RiskRow label="Humidity Risk" item={data.forecast_risk.humidity_risk} />
            <RiskRow label="Wind Risk" item={data.forecast_risk.wind_risk} />
          </div>
        </div>
      )}

      {/* Crop Health / Disease Risk trend */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-card bg-card p-5">
          <h3 className="mb-2 text-sm font-medium text-graphite">🌱 Crop Health Trend</h3>
          <p className="text-sm italic text-pewter">{data.health_history.reason}</p>
        </div>
        <div className="rounded-card bg-card p-5">
          <h3 className="mb-2 text-sm font-medium text-graphite">🦠 Disease Risk Trend</h3>
          <p className="text-sm italic text-pewter">{data.disease_history.reason}</p>
        </div>
      </div>

      {/* Smart Insights */}
      <div>
        <h2 className="mb-3 font-serif text-xl font-medium text-charcoal">💡 Smart Insights</h2>
        {data.insights.length === 0 ? (
          <EmptyState message="Not enough data yet to generate insights for this period." />
        ) : (
          <div className="rounded-card bg-card p-5">
            <ul className="space-y-2">
              {data.insights.map((insight, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-charcoal">
                  <span className="mt-1 size-1.5 shrink-0 rounded-full bg-forest-ink" />
                  {insight.text}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Plot comparison */}
      {siblingPlots.length > 1 && (
        <div>
          <h2 className="mb-3 font-serif text-xl font-medium text-charcoal">Compare Plots</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {siblingPlots.map((p) => (
              <Link
                key={p.plot_id}
                to={`/plots/${p.plot_id}/analytics`}
                className={cn(
                  "rounded-card bg-card p-4 text-sm transition-colors hover:bg-ash-gray/60",
                  p.plot_id === plotId && "ring-2 ring-forest-ink"
                )}
              >
                <p className="font-medium text-charcoal">{p.plot_name}</p>
                {p.crop && <p className="text-xs text-graphite">Crop: {p.crop.crop_name}</p>}
                <p className="mt-1 text-xs">
                  Disease Risk:{" "}
                  <span className={cn("font-medium", RISK_TEXT_COLOR[p.disease_risk.level ?? "UNKNOWN"])}>
                    {p.disease_risk.available ? p.disease_risk.level : "Unknown"}
                  </span>
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* AI Farm Advisor (reused, not duplicated) */}
      {data.advisor_summary.top_recommendation && (
        <div className="rounded-card border-l-4 border-forest-ink bg-sage-card p-5">
          <div className="mb-1 flex items-center gap-2">
            <Sparkles className="size-4 text-forest-ink" aria-hidden="true" />
            <h3 className="text-sm font-medium text-forest-ink">AI Farm Advisor</h3>
          </div>
          <p className="text-sm text-charcoal">{data.advisor_summary.top_recommendation}</p>
          <Link to={`/plots/${plotId}`} className="mt-2 inline-block text-xs font-medium text-forest-ink hover:underline">
            View full advisor →
          </Link>
        </div>
      )}

      {/* Data Sources */}
      <Accordion>
        <AccordionItem value="data-sources">
          <AccordionTrigger className="text-sm font-medium text-graphite">🔍 Data Sources</AccordionTrigger>
          <AccordionContent>
            <ul className="space-y-1 text-sm text-graphite">
              {Object.entries(data.data_sources).map(([key, value]) => (
                <li key={key}>
                  <span className="font-medium text-charcoal">{key.replace(/_/g, " ")}:</span> {value}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-pewter">Generated: {new Date(data.timestamp).toLocaleString()}</p>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
