import { useQuery } from "@tanstack/react-query"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { LocateFixed } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet"
import { Link } from "react-router-dom"

import { EmptyState } from "@/components/EmptyState"
import { ErrorState } from "@/components/ErrorState"
import { LoadingState } from "@/components/LoadingState"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { getPlotsIntelligence, type PlotIntelligence } from "@/lib/api"
import { cn } from "@/lib/utils"

// Leaflet's default marker icon URLs break under Vite's bundling; point them
// at the CDN copies instead of trying to resolve local package assets.
const youIcon = new L.DivIcon({
  className: "",
  html: '<div style="width:16px;height:16px;border-radius:9999px;background:#07503f;border:3px solid white"></div>',
  iconSize: [16, 16],
})

const COLOR_HEX = { safe: "#4a7a5e", warning: "#c9922b", critical: "#b3532f", unknown: "#9ca3af" } as const
type ColorKey = keyof typeof COLOR_HEX

function coloredIcon(color: ColorKey) {
  return new L.DivIcon({
    className: "",
    html: `<div style="width:20px;height:20px;border-radius:9999px;background:${COLOR_HEX[color]};border:2px solid white;box-shadow:0 0 0 1px rgba(0,0,0,0.15)"></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  })
}

type Layer = "weather" | "rainfall" | "temperature" | "humidity" | "crop_health" | "disease_risk" | "weather_risk" | "alerts"

const LAYERS: { value: Layer; label: string }[] = [
  { value: "weather", label: "🌦️ Weather" },
  { value: "alerts", label: "🔔 Alerts" },
  { value: "rainfall", label: "🌧️ Rainfall" },
  { value: "temperature", label: "🌡️ Temperature" },
  { value: "humidity", label: "💦 Humidity" },
  { value: "crop_health", label: "🌱 Crop Health" },
  { value: "disease_risk", label: "🦠 Disease Risk" },
  { value: "weather_risk", label: "⚠️ Weather Risk" },
  // 💧 Soil Moisture intentionally omitted -- no data source exists
  // anywhere in this project (see docs/FOUNDATION.md).
]

function colorForLayer(entry: PlotIntelligence, layer: Layer): ColorKey {
  switch (layer) {
    case "rainfall": {
      const s = entry.weather.rainfall_mm.status
      return s === "Above Normal" ? "critical" : s === "Elevated" ? "warning" : s === "Unknown" ? "unknown" : "safe"
    }
    case "temperature": {
      const s = entry.weather.temp_max_c.status
      return s === "High" ? "critical" : s === "Unknown" ? "unknown" : "safe"
    }
    case "humidity": {
      const s = entry.weather.rh_max_pct.status
      return s === "High" ? "warning" : s === "Unknown" ? "unknown" : "safe"
    }
    case "crop_health": {
      const s = entry.health.status
      return s === "POOR" ? "critical" : s === "FAIR" ? "warning" : s === "GOOD" ? "safe" : "unknown"
    }
    case "disease_risk": {
      const l = entry.disease_risk.level
      return l === "HIGH" ? "critical" : l === "MEDIUM" ? "warning" : l === "LOW" ? "safe" : "unknown"
    }
    case "weather_risk": {
      const l = entry.weather_risk.level
      return l === "HIGH" ? "critical" : l === "LOW" ? "safe" : "unknown"
    }
    case "alerts": {
      const s = entry.active_alerts.top_severity
      if (s === "critical") return "critical"
      if (s === "warning" || s === "attention") return "warning"
      if (s === "info") return "safe"
      return "safe" // no active alerts -- nothing requiring attention
    }
    default:
      return "unknown"
  }
}

const LEGENDS: Record<Layer, { label: string; color: ColorKey }[]> = {
  weather: [],
  rainfall: [
    { label: "Normal", color: "safe" },
    { label: "Elevated", color: "warning" },
    { label: "Above Normal", color: "critical" },
  ],
  temperature: [
    { label: "Suitable", color: "safe" },
    { label: "High", color: "critical" },
  ],
  humidity: [
    { label: "Normal", color: "safe" },
    { label: "High", color: "warning" },
  ],
  crop_health: [
    { label: "GOOD", color: "safe" },
    { label: "FAIR", color: "warning" },
    { label: "POOR", color: "critical" },
    { label: "Unknown", color: "unknown" },
  ],
  disease_risk: [
    { label: "LOW", color: "safe" },
    { label: "MEDIUM", color: "warning" },
    { label: "HIGH", color: "critical" },
    { label: "UNKNOWN", color: "unknown" },
  ],
  weather_risk: [
    { label: "LOW", color: "safe" },
    { label: "HIGH", color: "critical" },
    { label: "UNKNOWN", color: "unknown" },
  ],
  alerts: [
    { label: "Critical", color: "critical" },
    { label: "Warning / Attention", color: "warning" },
    { label: "No active alerts", color: "safe" },
  ],
}

/** Focuses the map on the farmer's own plots instead of a fixed
 * one-plot-or-Sathupally-centroid default -- so with 2+ located plots the
 * view isn't arbitrarily centered/zoomed on just the first one. */
function FitToPlots({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length < 2) return
    const bounds = L.latLngBounds(points)
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [32, 32], maxZoom: 14 })
  }, [points, map])
  return null
}

function RecenterButton({ onLocate }: { onLocate: (lat: number, lon: number) => void }) {
  const map = useMap()
  const [locating, setLocating] = useState(false)

  const useCurrentLocation = () => {
    if (!navigator.geolocation) return
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        map.setView([pos.coords.latitude, pos.coords.longitude], 13)
        onLocate(pos.coords.latitude, pos.coords.longitude)
        setLocating(false)
      },
      () => setLocating(false),
      { timeout: 8000 }
    )
  }

  return (
    <Button
      size="icon"
      variant="secondary"
      className="absolute right-3 top-3 z-[1000]"
      onClick={useCurrentLocation}
      disabled={locating}
      aria-label="Use current location"
    >
      <LocateFixed className="size-4" />
    </Button>
  )
}

function PlotPopupContent({ entry }: { entry: PlotIntelligence }) {
  return (
    <div className="min-w-52 space-y-2 text-sm">
      <p className="font-serif text-base font-medium text-charcoal">
        {entry.active_alerts.total > 0 && <span className="mr-1">{entry.active_alerts.top_emoji}</span>}
        {entry.plot_name}
      </p>
      <p className="text-xs text-graphite">Farm: {entry.farm_name}</p>
      {entry.active_alerts.total > 0 && (
        <p className="text-xs font-medium text-status-warning">
          {entry.active_alerts.total} active alert{entry.active_alerts.total > 1 ? "s" : ""}
        </p>
      )}
      {entry.crop && (
        <p className="text-xs text-graphite">
          Crop: {entry.crop.crop_name} {entry.crop.variety && `(${entry.crop.variety})`} · {entry.crop.stage}
        </p>
      )}

      <div className="border-t border-moss/40 pt-2">
        <p>
          <span className="font-medium">Crop Health:</span> {entry.health.available ? entry.health.status : "Unavailable"}
        </p>
        <p>
          <span className="font-medium">Disease Risk:</span>{" "}
          {entry.disease_risk.available ? entry.disease_risk.level : "Unknown"}
        </p>
        <p>
          <span className="font-medium">Weather Risk:</span>{" "}
          {entry.weather_risk.available ? entry.weather_risk.level : "Unknown"}
        </p>
      </div>

      <div className="border-t border-moss/40 pt-2">
        <p>Temp: {entry.weather.temp_max_c.value ?? "N/A"}°C</p>
        <p>Humidity: {entry.weather.rh_max_pct.value ?? "N/A"}%</p>
        <p>Rainfall: {entry.weather.rainfall_mm.value ?? "N/A"}mm ({entry.weather.rainfall_mm.source === "estimated_downscaled" ? "spatial estimate" : "GP-level"})</p>
      </div>

      {entry.top_recommendation && (
        <div className="border-t border-moss/40 pt-2">
          <p className="font-medium text-forest-ink">AI Action</p>
          <p>{entry.top_recommendation}</p>
        </div>
      )}

      <Link to={`/plots/${entry.plot_id}`} className="mt-2 block font-medium text-forest-ink hover:underline">
        View Farm Details →
      </Link>
    </div>
  )
}

export function FarmMap() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["plots-intelligence"], queryFn: getPlotsIntelligence })
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null)
  const [layer, setLayer] = useState<Layer>("weather")
  const [farmFilter, setFarmFilter] = useState("all")
  const [cropFilter, setCropFilter] = useState("all")
  const [stageFilter, setStageFilter] = useState("all")
  const [riskFilter, setRiskFilter] = useState("all")

  const entries = data ?? []
  const farmOptions = useMemo(() => [...new Set(entries.map((e) => e.farm_name))], [entries])
  const cropOptions = useMemo(() => [...new Set(entries.filter((e) => e.crop).map((e) => e.crop!.crop_name))], [entries])
  const stageOptions = useMemo(() => [...new Set(entries.filter((e) => e.crop).map((e) => e.crop!.stage))], [entries])

  const filtered = entries.filter((e) => {
    if (farmFilter !== "all" && e.farm_name !== farmFilter) return false
    if (cropFilter !== "all" && e.crop?.crop_name !== cropFilter) return false
    if (stageFilter !== "all" && e.crop?.stage !== stageFilter) return false
    if (riskFilter !== "all") {
      const level = e.disease_risk.available ? e.disease_risk.level : "UNKNOWN"
      if (level !== riskFilter) return false
    }
    return true
  })

  const located = filtered.filter((e) => e.location_configured)
  const unlocated = filtered.filter((e) => !e.location_configured)

  if (isLoading) return <LoadingState label="Loading farm intelligence..." />
  if (isError) return <ErrorState message="Unable to load the farm intelligence map." onRetry={() => refetch()} />
  if (entries.length === 0) return <EmptyState message="Add a plot to see it on the Farm Intelligence Map." />

  const healthy = filtered.filter((e) => e.health.status === "GOOD").length
  const moderate = filtered.filter((e) => e.health.status === "FAIR").length
  const highConcern = filtered.filter((e) => e.health.status === "POOR").length
  const diseaseLow = filtered.filter((e) => e.disease_risk.level === "LOW").length
  const diseaseMedium = filtered.filter((e) => e.disease_risk.level === "MEDIUM").length
  const diseaseHigh = filtered.filter((e) => e.disease_risk.level === "HIGH").length
  const diseaseUnknown = filtered.filter((e) => !e.disease_risk.available).length

  const center: [number, number] = located[0] ? [located[0].latitude!, located[0].longitude!] : [17.2, 80.85]

  return (
    <div className="space-y-4">
      {/* Farm Overview */}
      <div className="rounded-card bg-card p-5">
        <h3 className="mb-3 text-sm font-medium text-graphite">Farm Overview</h3>
        <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <p className="text-xs text-pewter">Total plots</p>
            <p className="text-lg font-medium text-charcoal">{filtered.length}</p>
          </div>
          <div>
            <p className="text-xs text-pewter">Healthy / Moderate / High concern</p>
            <p className="text-lg font-medium text-charcoal">
              {healthy} / {moderate} / {highConcern}
            </p>
          </div>
          <div>
            <p className="text-xs text-pewter">Disease Risk Low / Medium / High</p>
            <p className="text-lg font-medium text-charcoal">
              {diseaseLow} / {diseaseMedium} / {diseaseHigh}
            </p>
          </div>
          <div>
            <p className="text-xs text-pewter">Unknown risk</p>
            <p className="text-lg font-medium text-charcoal">{diseaseUnknown}</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <FilterSelect label="Farm" value={farmFilter} onChange={setFarmFilter} options={farmOptions} />
        <FilterSelect label="Crop" value={cropFilter} onChange={setCropFilter} options={cropOptions} />
        <FilterSelect label="Growth stage" value={stageFilter} onChange={setStageFilter} options={stageOptions} />
        <FilterSelect label="Risk" value={riskFilter} onChange={setRiskFilter} options={["LOW", "MEDIUM", "HIGH", "UNKNOWN"]} />
      </div>

      {/* Layer selector */}
      <div className="flex flex-wrap gap-2">
        {LAYERS.map((l) => (
          <button
            key={l.value}
            type="button"
            onClick={() => setLayer(l.value)}
            className={cn(
              "rounded-nav-pill px-3 py-1.5 text-xs font-medium transition-colors",
              layer === l.value ? "bg-forest-ink text-white" : "bg-ash-gray text-graphite hover:bg-moss/40"
            )}
          >
            {l.label}
          </button>
        ))}
      </div>

      {/* Map -- capped height so it never dominates the screen */}
      <div className="relative overflow-hidden rounded-card">
        <MapContainer center={center} zoom={11} scrollWheelZoom={false} style={{ height: 360, width: "100%" }} className="h-[280px] sm:h-[360px]">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <RecenterButton onLocate={(lat, lon) => setUserLocation([lat, lon])} />
          <FitToPlots points={located.map((e): [number, number] => [e.latitude!, e.longitude!])} />

          {located.map((entry) => (
            <Marker key={entry.plot_id} position={[entry.latitude!, entry.longitude!]} icon={coloredIcon(colorForLayer(entry, layer))}>
              <Popup>
                <PlotPopupContent entry={entry} />
              </Popup>
            </Marker>
          ))}

          {userLocation && (
            <Marker position={userLocation} icon={youIcon}>
              <Popup>Your current location</Popup>
            </Marker>
          )}
        </MapContainer>

        {/* Legend */}
        {LEGENDS[layer].length > 0 && (
          <div className="absolute bottom-3 left-3 z-[1000] rounded-card bg-card/95 p-3 text-xs shadow-none ring-1 ring-moss">
            {LEGENDS[layer].map((item) => (
              <div key={item.label} className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full" style={{ backgroundColor: COLOR_HEX[item.color] }} />
                {item.label}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Plots without location */}
      {unlocated.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-graphite">Plots without location</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {unlocated.map((entry) => (
              <Link
                key={entry.plot_id}
                to={`/plots/${entry.plot_id}`}
                className="rounded-card bg-card p-4 text-sm transition-colors hover:bg-ash-gray/60"
              >
                <p className="font-medium text-charcoal">{entry.plot_name}</p>
                <p className="text-xs italic text-status-warning">Location not configured</p>
                <p className="mt-1 text-xs text-graphite">{entry.farm_name}</p>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: string[]
}) {
  return (
    <Select value={value} onValueChange={(v) => v && onChange(v)}>
      <SelectTrigger className="w-40" size="sm">
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">{label}: All</SelectItem>
        {options.map((opt) => (
          <SelectItem key={opt} value={opt}>
            {opt}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
