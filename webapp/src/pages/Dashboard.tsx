import { useQueries, useQuery } from "@tanstack/react-query"
import { MapPin } from "lucide-react"
import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import { AdvisoryCard } from "@/components/AdvisoryCard"
import { AlertCard } from "@/components/AlertCard"
import { DistrictIntelligenceMap } from "@/components/DistrictIntelligenceMap"
import { EmptyState } from "@/components/EmptyState"
import { ErrorState } from "@/components/ErrorState"
import { HourlyForecast } from "@/components/HourlyForecast"
import { LoadingState } from "@/components/LoadingState"
import { LocationSelectStep } from "@/components/LocationSelectStep"
import { RecommendationCard } from "@/components/RecommendationCard"
import { RiskIndicator } from "@/components/RiskIndicator"
import { RiskLevelCard } from "@/components/RiskLevelCard"
import { TodayOutlookCharts } from "@/components/TodayOutlookCharts"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { WeatherCard } from "@/components/WeatherCard"
import { buildAdvisoryDetail } from "@/lib/advisory"
import {
  getAlertCenterAlerts,
  getAlertsForGp,
  getCropAdvisoryForFarm,
  getCurrentWeather,
  getFarmAdvisor,
  getForecastForGp,
  getHourlyEstimated,
  listFarms,
  listPlots,
  type AlertSeverity4,
} from "@/lib/api"
import { useAuth } from "@/lib/AuthProvider"
import { STATE } from "@/lib/telanganaLocations"
import { useSelectedGp } from "@/lib/useSelectedGp"

const ALERT_SEVERITY_RANK: Record<AlertSeverity4, number> = { critical: 0, warning: 1, attention: 2, info: 3 }

export function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [changingLocation, setChangingLocation] = useState(false)
  const { gps, selectedGp, selectGp } = useSelectedGp()

  const current = useQuery({
    queryKey: ["weather-current", selectedGp],
    queryFn: () => getCurrentWeather(selectedGp),
    enabled: !!selectedGp,
  })
  const hourly = useQuery({
    queryKey: ["weather-hourly", selectedGp],
    queryFn: () => getHourlyEstimated(selectedGp),
    enabled: !!selectedGp,
  })
  const alerts = useQuery({
    queryKey: ["alerts", selectedGp],
    queryFn: () => getAlertsForGp(selectedGp),
    enabled: !!selectedGp,
  })
  const forecast = useQuery({
    queryKey: ["forecast", selectedGp],
    queryFn: () => getForecastForGp(selectedGp),
    enabled: !!selectedGp,
  })
  const farms = useQuery({ queryKey: ["farms"], queryFn: listFarms })
  const primaryFarm = farms.data?.[0]
  const plots = useQuery({
    queryKey: ["plots", primaryFarm?.id],
    queryFn: () => listPlots(primaryFarm!.id),
    enabled: !!primaryFarm,
  })
  const primaryPlot = plots.data?.[0]
  const advisor = useQuery({
    queryKey: ["farm-advisor", primaryPlot?.id],
    queryFn: () => getFarmAdvisor(primaryPlot!.id),
    enabled: !!primaryPlot,
  })
  const cropAdvisoryQueries = useQueries({
    queries: (farms.data ?? []).map((farm) => ({
      queryKey: ["crop-advisory", farm.id],
      queryFn: () => getCropAdvisoryForFarm(farm.id),
    })),
  })
  const atRiskCrops = cropAdvisoryQueries.flatMap((q) => q.data ?? []).filter((a) => a.severity !== "safe")
  const allAlerts = useQuery({ queryKey: ["alert-center"], queryFn: getAlertCenterAlerts })

  if (!user?.selected_district || !user?.selected_block || changingLocation) {
    const alreadyHasLocation = !!user?.selected_district && !!user?.selected_block
    return (
      <LocationSelectStep
        initialDistrict={user?.selected_district ?? ""}
        initialBlock={user?.selected_block ?? ""}
        onDone={alreadyHasLocation ? () => setChangingLocation(false) : undefined}
      />
    )
  }

  if (!selectedGp || current.isLoading || forecast.isLoading) return <LoadingState />
  if (current.isError || !current.data || forecast.isError || !forecast.data) {
    return <ErrorState message="Unable to load weather for this Gram Panchayat." onRetry={() => current.refetch()} />
  }

  const today = current.data
  const todaysAlert = alerts.data?.find((a) => a.date === today.date)
  const advisoryDetail = todaysAlert
    ? { severity: todaysAlert.severity, what: todaysAlert.title, why: todaysAlert.description, action: todaysAlert.action }
    : buildAdvisoryDetail(today)

  const activeAlerts = [...(allAlerts.data ?? [])]
    .filter((a) => a.status !== "resolved" && a.status !== "expired")
    .sort((a, b) => ALERT_SEVERITY_RANK[a.severity] - ALERT_SEVERITY_RANK[b.severity])
  const topAlerts = activeAlerts.slice(0, 3)

  const irrigationRec = advisor.data?.recommendations.find((r) => r.category === "irrigation")

  return (
    <div className="space-y-6">
      {/* A. Location header */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-card bg-card p-4">
        <div className="flex items-center gap-2 text-sm">
          <MapPin className="size-4 shrink-0 text-forest-ink" aria-hidden="true" />
          <span className="font-medium text-charcoal">
            {user.selected_state ?? STATE} • {user.selected_district} • {user.selected_block}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedGp} onValueChange={(gp) => gp && selectGp(gp)}>
            <SelectTrigger className="w-44" title="Gram Panchayat">
              <SelectValue placeholder="Select GP" />
            </SelectTrigger>
            <SelectContent>
              {gps.map((gp) => (
                <SelectItem key={gp.gram_panchayat} value={gp.gram_panchayat}>
                  {gp.gram_panchayat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={() => setChangingLocation(true)}>
            Change Location
          </Button>
        </div>
      </div>

      {/* B. Current weather */}
      <WeatherCard row={today} />

      {/* C. Today's hourly outlook */}
      {hourly.data && <HourlyForecast points={hourly.data.points} />}

      {/* D. Today's outlook -- visual graphs */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">Today's Outlook</h2>
        <TodayOutlookCharts rows={forecast.data} />
      </div>

      {/* E. Current alerts */}
      <div>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="font-serif text-lg font-medium text-charcoal">⚠️ Alerts</h2>
          {activeAlerts.length > 0 && (
            <Link to="/alerts" className="text-sm font-medium text-forest-ink hover:underline">
              View All Alerts →
            </Link>
          )}
        </div>
        {topAlerts.length === 0 ? (
          <div className="rounded-card bg-status-safe-bg p-4 text-sm font-medium text-status-safe">
            ✓ No critical alerts for your selected location.
          </div>
        ) : (
          <div className="space-y-3">
            {topAlerts.map((a) => (
              <AlertCard key={a.id} alert={a} />
            ))}
          </div>
        )}
      </div>

      {/* F. ML farm intelligence */}
      <div>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="font-serif text-lg font-medium text-charcoal">🌱 ML Farm Intelligence</h2>
          {primaryPlot && (
            <Link to={`/plots/${primaryPlot.id}`} className="text-sm font-medium text-forest-ink hover:underline">
              View Details →
            </Link>
          )}
        </div>

        {primaryPlot && advisor.data ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <RiskLevelCard
              title="🦠 Disease Risk"
              level={advisor.data.disease_risk.level}
              why={advisor.data.disease_risk.why}
              classification={advisor.data.disease_risk.classification}
            />
            <RiskLevelCard
              title="🌡 Weather Risk"
              level={advisor.data.weather_risk.level}
              why={advisor.data.weather_risk.why}
              classification={advisor.data.weather_risk.classification}
            />
            {irrigationRec && <RecommendationCard recommendation={irrigationRec} />}
          </div>
        ) : atRiskCrops.length > 0 ? (
          <div className="space-y-3 rounded-card bg-card p-6">
            {atRiskCrops.map((a) => (
              <div key={a.crop_id} className="flex items-start justify-between gap-3 border-b border-moss/30 pb-3 last:border-0 last:pb-0">
                <div>
                  <p className="text-sm font-medium text-charcoal">
                    {a.crop_name} — {a.stage}
                  </p>
                  <p className="text-sm text-graphite">{a.action}</p>
                </div>
                <RiskIndicator severity={a.severity} />
              </div>
            ))}
          </div>
        ) : farms.data && farms.data.length > 0 ? (
          <EmptyState message="No elevated crop risk right now — configure a plot in My Farm for detailed disease/weather/irrigation intelligence." />
        ) : (
          <EmptyState
            message="Add a farm to see crop intelligence for your fields."
            actionLabel="Add Farm"
            onAction={() => navigate("/farm")}
          />
        )}
      </div>

      {/* G. Today's farm advisory */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🌾 Today's Farm Advisory</h2>
        {primaryPlot && advisor.data && advisor.data.action_plan.length > 0 ? (
          <div className="rounded-card border-l-4 border-status-warning bg-status-warning-bg p-5">
            <p className="font-medium text-charcoal">
              🚨 {advisor.data.action_plan.length} action{advisor.data.action_plan.length > 1 ? "s" : ""} recommended
            </p>
            <ul className="mt-2 space-y-1 text-sm text-charcoal">
              {advisor.data.action_plan.slice(0, 3).map((item) => (
                <li key={item.category}>• {item.label}</li>
              ))}
            </ul>
            <Link to="/advisory" className="mt-3 inline-block text-sm font-medium text-forest-ink hover:underline">
              View Full Advisory →
            </Link>
          </div>
        ) : (
          <AdvisoryCard
            {...advisoryDetail}
            dateLabel={new Date(today.date).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
            prominent
          />
        )}
      </div>

      {/* H. District block intelligence map */}
      <div className="rounded-card bg-card p-6">
        <h2 className="mb-4 font-serif text-lg font-medium text-charcoal">🗺 District Intelligence</h2>
        <DistrictIntelligenceMap district={user.selected_district} selectedBlock={user.selected_block} selectedGp={selectedGp} />
      </div>
    </div>
  )
}
