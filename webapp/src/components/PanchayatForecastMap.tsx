import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { useEffect, useMemo, useState } from "react"
import { CircleMarker, GeoJSON, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet"

import { EmptyState } from "@/components/EmptyState"
import { classifyForecastRow } from "@/lib/advisory"
import type { ForecastRow, GpCentroid } from "@/lib/api"
import { cn } from "@/lib/utils"

// Same thresholds used throughout the backend (advisory_rules.py) -- mirrored
// here, not reinvented.
const HEAVY_RAIN_THRESHOLD_MM = 20
const HEAT_STRESS_THRESHOLD_C = 38
const HUMID_RH_THRESHOLD_PCT = 85
const HUMID_RAIN_THRESHOLD_MM = 5

export type MapLayer = "rainfall" | "temperature" | "humidity" | "wind" | "risk"

const LAYERS: { value: MapLayer; label: string; emoji: string }[] = [
  { value: "rainfall", label: "Rainfall", emoji: "\u{1F327}" },
  { value: "temperature", label: "Temperature", emoji: "\u{1F321}" },
  { value: "humidity", label: "Humidity", emoji: "\u{1F4A7}" },
  { value: "wind", label: "Wind", emoji: "\u{1F4A8}" },
  { value: "risk", label: "Weather Risk", emoji: "⚠️" },
]

const COLOR = { safe: "#4a7a5e", warning: "#c9922b", critical: "#b3532f", unavailable: "#c9cbc5" } as const
type ColorKey = keyof typeof COLOR

function colorForLayer(layer: MapLayer, row: ForecastRow | undefined): ColorKey {
  if (!row) return "unavailable"
  switch (layer) {
    case "rainfall":
      if (row.rainfall_mm == null) return "unavailable"
      return row.rainfall_mm > HEAVY_RAIN_THRESHOLD_MM ? "critical" : row.rainfall_mm > HUMID_RAIN_THRESHOLD_MM ? "warning" : "safe"
    case "temperature":
      return row.temp_max_c == null ? "unavailable" : row.temp_max_c > HEAT_STRESS_THRESHOLD_C ? "critical" : "safe"
    case "humidity":
      return row.rh_max_pct == null ? "unavailable" : row.rh_max_pct > HUMID_RH_THRESHOLD_PCT ? "warning" : "safe"
    case "wind":
      // No wind-risk threshold exists anywhere in this system (see
      // src/analytics.py) -- never fabricate one; shown as a raw value only.
      return row.wind_max_kmh == null ? "unavailable" : "safe"
    case "risk":
      return classifyForecastRow(row).severity
    default:
      return "unavailable"
  }
}

function FitToFeature({ feature }: { feature: GeoJSON.Feature | null }) {
  const map = useMap()
  useEffect(() => {
    if (!feature) return
    map.invalidateSize()
    const bounds = L.geoJSON(feature).getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [24, 24] })
  }, [feature, map])
  return null
}

export function PanchayatForecastMap({
  block,
  blockFeature,
  gps,
  rowsByGpAndDate,
  dates,
  selectedGp,
  onSelectGp,
}: {
  block: string
  /** The one real mandal/block boundary feature matching `block`, or null if
   * boundary geometry isn't available for it (never fabricated). */
  blockFeature: GeoJSON.Feature | null
  gps: GpCentroid[]
  rowsByGpAndDate: Map<string, Map<string, ForecastRow>>
  dates: string[]
  selectedGp: string
  onSelectGp: (gp: string) => void
}) {
  const [layer, setLayer] = useState<MapLayer>("rainfall")
  const [mapDate, setMapDate] = useState(dates[0] ?? "")

  const activeDate = dates.includes(mapDate) ? mapDate : dates[0]

  const rowsForDate = useMemo(() => {
    const map = new Map<string, ForecastRow>()
    for (const gp of gps) {
      const row = rowsByGpAndDate.get(gp.gram_panchayat)?.get(activeDate)
      if (row) map.set(gp.gram_panchayat, row)
    }
    return map
  }, [gps, rowsByGpAndDate, activeDate])

  if (!blockFeature) {
    return <EmptyState message={`Block boundary data is not available for ${block || "this block"} yet.`} />
  }

  const showsRiskTiers = layer !== "wind"

  return (
    <div className="space-y-3">
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
            {l.emoji} {l.label}
          </button>
        ))}
      </div>

      {dates.length > 1 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-graphite">Forecast date:</span>
          {dates.map((d, i) => (
            <button
              key={d}
              type="button"
              onClick={() => setMapDate(d)}
              className={cn(
                "rounded-nav-pill px-3 py-1 text-xs font-medium transition-colors",
                activeDate === d ? "bg-forest-ink text-white" : "bg-ash-gray text-graphite hover:bg-moss/40"
              )}
            >
              {i === 0 ? "Today" : new Date(d).toLocaleDateString(undefined, { weekday: "short", day: "numeric" })}
            </button>
          ))}
        </div>
      )}

      <div className="mx-auto max-w-2xl overflow-hidden rounded-card">
        <MapContainer center={[17.24, 80.6]} zoom={12} scrollWheelZoom={false} style={{ aspectRatio: "1 / 1", width: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            opacity={0.55}
          />
          <FitToFeature feature={blockFeature} />
          <GeoJSON
            data={blockFeature}
            style={{ fillColor: "transparent", color: "#07503f", weight: 2.5 }}
          />
          {gps.map((gp) => {
            const row = rowsForDate.get(gp.gram_panchayat)
            const isSelected = gp.gram_panchayat === selectedGp
            return (
              <CircleMarker
                key={gp.gram_panchayat}
                center={[gp.latitude, gp.longitude]}
                radius={isSelected ? 10 : 7}
                pathOptions={{
                  fillColor: COLOR[colorForLayer(layer, row)],
                  fillOpacity: 0.9,
                  color: isSelected ? "#07503f" : "#ffffff",
                  weight: isSelected ? 3 : 1.5,
                }}
                eventHandlers={{ click: () => onSelectGp(gp.gram_panchayat) }}
              >
                <Tooltip direction="top" offset={[0, -8]}>
                  <div className="space-y-0.5 text-xs">
                    <p className="font-medium">{gp.gram_panchayat}</p>
                    <p>
                      {"\u{1F321}"} {row?.temp_max_c != null ? `${row.temp_max_c.toFixed(1)}°C` : "Data unavailable"}
                    </p>
                    <p>
                      {"\u{1F4A7}"} {row?.rh_max_pct != null ? `${row.rh_max_pct.toFixed(0)}%` : "Data unavailable"}
                    </p>
                    <p>
                      {"\u{1F327}"} {row?.rainfall_mm != null ? `${row.rainfall_mm.toFixed(1)}mm` : "Data unavailable"}
                    </p>
                    <p>
                      {"\u{1F4A8}"} {row?.wind_max_kmh != null ? `${row.wind_max_kmh.toFixed(1)}km/h` : "Data unavailable"}
                    </p>
                    <p className="italic text-pewter">Tap to view its full forecast</p>
                  </div>
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded-card bg-card p-4 text-xs text-graphite">
        <span className="font-medium text-charcoal">Legend:</span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ backgroundColor: COLOR.safe }} /> {showsRiskTiers ? "Low" : "Available"}
        </span>
        {showsRiskTiers && (
          <>
            <span className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-full" style={{ backgroundColor: COLOR.warning }} /> Medium
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-full" style={{ backgroundColor: COLOR.critical }} /> High
            </span>
          </>
        )}
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ backgroundColor: COLOR.unavailable }} /> Data unavailable
        </span>
      </div>
      <p className="text-xs italic text-pewter">
        Rainfall varies per Panchayat (real ML-downscaled forecast). Temperature/humidity/wind are the block
        forecast passed through unchanged (identical across all Panchayats) -- no gridded source exists yet to
        downscale them. Weather Risk is a derived, threshold-based assessment, not an ML prediction.
      </p>
    </div>
  )
}
