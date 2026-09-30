import { useQuery } from "@tanstack/react-query"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { useEffect, useState } from "react"
import { CircleMarker, GeoJSON, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet"

import { EmptyState } from "@/components/EmptyState"
import { LoadingState } from "@/components/LoadingState"
import { getForecast, getGps, type ForecastRow } from "@/lib/api"
import { MANDAL_WITH_DATA } from "@/lib/telanganaLocations"
import { useKhammamMandalsGeoJson, type MandalFeature } from "@/lib/useKhammamMandalsGeoJson"
import { cn } from "@/lib/utils"

// Same thresholds used throughout the backend (advisory_rules.py) -- mirrored
// here, not reinvented, so this map's colors agree with every other screen.
const HEAVY_RAIN_THRESHOLD_MM = 20
const HEAT_STRESS_THRESHOLD_C = 38
const HUMID_RH_THRESHOLD_PCT = 85
const HUMID_RAIN_THRESHOLD_MM = 5

type Layer = "temperature" | "humidity" | "rainfall" | "wind"

const LAYERS: { value: Layer; label: string; emoji: string }[] = [
  { value: "temperature", label: "Temperature", emoji: "\u{1F321}" },
  { value: "humidity", label: "Humidity", emoji: "\u{1F4A7}" },
  { value: "rainfall", label: "Rainfall", emoji: "\u{1F327}" },
  { value: "wind", label: "Wind", emoji: "\u{1F4A8}" },
]

const COLOR = { safe: "#4a7a5e", warning: "#c9922b", critical: "#b3532f", unavailable: "#c9cbc5" } as const
type ColorKey = keyof typeof COLOR

type WeatherFields = Pick<ForecastRow, "rainfall_mm" | "temp_max_c" | "rh_max_pct" | "wind_max_kmh">

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

/** No wind-risk threshold has ever been established anywhere in this system
 * (see src/analytics.py) -- so wind is never risk-colored, only shown as a
 * real value. Rainfall/temperature/humidity reuse the exact thresholds
 * already used by the backend's own advisory rules. */
function colorForLayer(layer: Layer, row: WeatherFields | undefined): ColorKey {
  if (!row) return "unavailable"
  switch (layer) {
    case "rainfall":
      if (row.rainfall_mm == null) return "unavailable"
      return row.rainfall_mm > HEAVY_RAIN_THRESHOLD_MM ? "critical" : row.rainfall_mm > HUMID_RAIN_THRESHOLD_MM ? "warning" : "safe"
    case "temperature":
      if (row.temp_max_c == null) return "unavailable"
      return row.temp_max_c > HEAT_STRESS_THRESHOLD_C ? "critical" : "safe"
    case "humidity":
      if (row.rh_max_pct == null) return "unavailable"
      return row.rh_max_pct > HUMID_RH_THRESHOLD_PCT ? "warning" : "safe"
    case "wind":
      return row.wind_max_kmh == null ? "unavailable" : "safe"
    default:
      return "unavailable"
  }
}

/** Rainfall is the one variable the real trained model actually varies
 * per-GP; temp/humidity/wind are pass-through copies of the block forecast
 * (see docs/FOUNDATION.md section B) -- never presented as if they varied. */
const LAYER_SOURCE_NOTE: Record<Layer, string> = {
  rainfall: "ML-downscaled forecast, real per-Panchayat variation",
  temperature: "Block forecast (pass-through) -- identical across all Panchayats",
  humidity: "Block forecast (pass-through) -- identical across all Panchayats",
  wind: "Block forecast (pass-through) -- no risk threshold established in this system yet",
}

function formatValue(layer: Layer, row: WeatherFields | undefined): string {
  if (!row) return "Data unavailable"
  switch (layer) {
    case "rainfall":
      return row.rainfall_mm != null ? `${row.rainfall_mm.toFixed(1)}mm` : "Data unavailable"
    case "temperature":
      return row.temp_max_c != null ? `${row.temp_max_c.toFixed(1)}°C` : "Data unavailable"
    case "humidity":
      return row.rh_max_pct != null ? `${row.rh_max_pct.toFixed(0)}%` : "Data unavailable"
    case "wind":
      return row.wind_max_kmh != null ? `${row.wind_max_kmh.toFixed(1)}km/h` : "Data unavailable"
  }
}

function averageRow(rows: WeatherFields[]): WeatherFields | undefined {
  if (rows.length === 0) return undefined
  const avg = (key: keyof WeatherFields) => {
    const vals = rows.map((r) => r[key]).filter((v): v is number => v != null)
    return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null
  }
  return { rainfall_mm: avg("rainfall_mm"), temp_max_c: avg("temp_max_c"), rh_max_pct: avg("rh_max_pct"), wind_max_kmh: avg("wind_max_kmh") }
}

function FitToMandals({ features }: { features: MandalFeature[] }) {
  const map = useMap()
  useEffect(() => {
    if (features.length === 0) return
    // The map sits far down a long page whose content above it (weather
    // cards, charts) can still be settling layout when Leaflet first reads
    // its container size -- invalidateSize forces a fresh read before
    // fitBounds, otherwise it fits against a stale/incorrect size and the
    // district ends up a speck in a near-India-wide view.
    map.invalidateSize()
    const layer = L.geoJSON(features as unknown as GeoJSON.GeoJsonObject)
    const bounds = layer.getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [6, 6] })
  }, [features, map])
  return null
}

export function DistrictIntelligenceMap({
  district,
  selectedBlock,
  selectedGp,
}: {
  district: string
  selectedBlock: string
  /** Optional: highlights this Gram Panchayat's point on the map. */
  selectedGp?: string
}) {
  const [layer, setLayer] = useState<Layer>("temperature")
  const mandalsQuery = useKhammamMandalsGeoJson()
  const gpsQuery = useQuery({ queryKey: ["gps"], queryFn: getGps })
  const forecastQuery = useQuery({ queryKey: ["forecast-all"], queryFn: getForecast })

  const hasBoundaryData = district === "Khammam"

  if (!hasBoundaryData) {
    return <EmptyState message={`Block boundary data is not available for ${district || "this district"} yet.`} />
  }
  if (mandalsQuery.isLoading || forecastQuery.isLoading || gpsQuery.isLoading) return <LoadingState label="Loading district map..." />
  if (mandalsQuery.isError || !mandalsQuery.data) return <EmptyState message="Block boundary data failed to load." />

  const gpPoints = gpsQuery.data ?? []
  const today = todayIso()
  const allRows = forecastQuery.data ?? []
  const rowsByGp = new Map<string, ForecastRow>()
  for (const r of allRows) {
    if (r.date === today) rowsByGp.set(r.gram_panchayat, r)
  }
  if (rowsByGp.size === 0) {
    // Demo/seed data may not span "today" -- fall back to each GP's most
    // recent real row rather than showing everything as unavailable.
    for (const r of allRows) {
      if (!rowsByGp.has(r.gram_panchayat)) rowsByGp.set(r.gram_panchayat, r)
    }
  }
  const weatherPointCount = gpPoints.filter((gp) => rowsByGp.has(gp.gram_panchayat)).length

  const representativeRow = averageRow([...rowsByGp.values()])
  const activeColor = colorForLayer(layer, representativeRow)
  const showsRiskTiers = layer !== "wind"

  const styleFor = (feature?: MandalFeature) => {
    const isDataBlock = feature?.properties.mandal === MANDAL_WITH_DATA
    const isSelected = feature?.properties.mandal === selectedBlock
    return {
      fillColor: isDataBlock ? COLOR[activeColor] : COLOR.unavailable,
      fillOpacity: isDataBlock ? 0.55 : 0.35,
      color: isSelected ? "#07503f" : "#8a8f86",
      weight: isSelected ? 3 : 1.25,
    }
  }

  return (
    <div className="space-y-3">
      {/* Real counts -- never hardcoded: blocks = boundary features actually
       * loaded, Panchayats = /gps centroids, Weather Points = Panchayats
       * that actually have a forecast row for today. */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 rounded-card bg-card p-4 text-sm">
        <span className="font-serif font-medium text-charcoal">{district} District</span>
        <span className="text-graphite">
          Blocks: <strong className="text-charcoal">{mandalsQuery.data.features.length}</strong>
        </span>
        <span className="text-graphite">
          Panchayats: <strong className="text-charcoal">{gpPoints.length}</strong>
        </span>
        <span className="text-graphite">
          Weather Points: <strong className="text-charcoal">{weatherPointCount}</strong>
        </span>
      </div>

      {/* Weather variable controls -- above the map. */}
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

      {/* Aspect ratio close to Khammam's own bounding-box shape (~0.8) so
       * fitBounds zooms in tight on the district instead of stretching to a
       * wide strip that pulls in half of Telangana as "context". Sized
       * larger (up to 3xl) so the district reads as the main content, not a
       * small inset. */}
      <div className="mx-auto max-w-3xl overflow-hidden rounded-card">
        <MapContainer center={[17.24, 80.6]} zoom={9} scrollWheelZoom={false} style={{ aspectRatio: "4 / 5", width: "100%" }}>
          {/* Muted opacity -- this is an administrative boundary view, not a
           * street map, so base-tile clutter (roads, terrain, city labels)
           * should recede and let the mandal/Panchayat markers read as the
           * content. (CARTO's free basemaps now require an API key, so this
           * stays on the no-key-required public OSM tile server.) */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            opacity={0.55}
          />
          <FitToMandals features={mandalsQuery.data.features} />
          <GeoJSON
            key={layer}
            data={mandalsQuery.data as unknown as GeoJSON.FeatureCollection}
            style={styleFor as never}
            onEachFeature={(feature, geoLayer) => {
              const name = feature.properties.mandal as string
              const isDataBlock = name === MANDAL_WITH_DATA
              geoLayer.bindTooltip(name, { sticky: true })
              geoLayer.bindPopup(
                isDataBlock && representativeRow
                  ? `<strong>${name}</strong> (selected: ${selectedBlock === name ? "yes" : "no"})<br/>` +
                      `${LAYERS.find((l) => l.value === layer)?.label}: ${formatValue(layer, representativeRow)} (block average)<br/>` +
                      `<em>${LAYER_SOURCE_NOTE[layer]}</em>`
                  : `<strong>${name}</strong><br/>Data unavailable`
              )
            }}
          />

          {/* Every real GP/weather point -- these ARE this district's real
           * Panchayat points (this project's spatial resolution is exactly
           * Gram Panchayat level, see docs/FOUNDATION.md). No fake points. */}
          {gpPoints.map((gp) => {
            const row = rowsByGp.get(gp.gram_panchayat)
            const isSelected = gp.gram_panchayat === selectedGp
            return (
              <CircleMarker
                key={gp.gram_panchayat}
                center={[gp.latitude, gp.longitude]}
                radius={isSelected ? 8 : 5}
                pathOptions={{
                  fillColor: COLOR[colorForLayer(layer, row)],
                  fillOpacity: 0.9,
                  color: isSelected ? "#07503f" : "#ffffff",
                  weight: isSelected ? 3 : 1.5,
                }}
              >
                <Tooltip direction="top" offset={[0, -6]}>
                  <div className="space-y-0.5 text-xs">
                    <p className="font-medium">
                      {"\u{1F4CD}"} {gp.gram_panchayat} (Panchayat)
                    </p>
                    <p>{"\u{1F321}"} Temperature: {row?.temp_max_c != null ? `${row.temp_max_c.toFixed(1)}°C` : "Data unavailable"}</p>
                    <p>{"\u{1F4A7}"} Humidity: {row?.rh_max_pct != null ? `${row.rh_max_pct.toFixed(0)}%` : "Data unavailable"}</p>
                    <p>{"\u{1F327}"} Rainfall: {row?.rainfall_mm != null ? `${row.rainfall_mm.toFixed(1)}mm` : "Data unavailable"}</p>
                    <p>{"\u{1F4A8}"} Wind: {row?.wind_max_kmh != null ? `${row.wind_max_kmh.toFixed(1)}km/h` : "Data unavailable"}</p>
                    <p>{"\u{1F550}"} {row?.date ?? "Data unavailable"}</p>
                    <p className="italic text-pewter">Rainfall: ML-downscaled per Panchayat. Temp/humidity/wind: block-level (pass-through).</p>
                  </div>
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded-card bg-card p-4 text-xs text-graphite">
        <span className="font-medium text-charcoal">Legend ({LAYERS.find((l) => l.value === layer)?.label}):</span>
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
        {LAYER_SOURCE_NOTE[layer]}. Only {MANDAL_WITH_DATA} mandal has a real downscaled forecast (block average
        shown on the shaded polygon); every other Khammam mandal boundary is real but carries no pipeline data yet.
        All {gpPoints.length} Panchayat points above are real, hover any point for its own values.
      </p>
    </div>
  )
}
