import { CloudDrizzle, CloudRain, Droplets, Sun, Wind } from "lucide-react"

import { RiskIndicator } from "@/components/RiskIndicator"
import { classifyForecastRow } from "@/lib/advisory"
import type { ForecastRow } from "@/lib/api"
import { cn } from "@/lib/utils"

/** A simple, honestly-derived icon from the real rainfall figure -- not a
 * separate weather-condition model (mirrors src/analytics.py's own
 * condition_label(), which is the same kind of plain derivation). */
const CONDITION_ICONS = { heavy: CloudRain, light: CloudDrizzle, clear: Sun } as const

function conditionFor(row: ForecastRow): keyof typeof CONDITION_ICONS {
  if (row.rainfall_mm != null && row.rainfall_mm > 20) return "heavy"
  if (row.rainfall_mm != null && row.rainfall_mm > 0) return "light"
  return "clear"
}

function dayLabel(dateStr: string, isFirst: boolean): string {
  if (isFirst) return "TODAY"
  return new Date(dateStr).toLocaleDateString(undefined, { weekday: "short" }).toUpperCase()
}

export function DailyForecastCard({
  row,
  isFirst,
  selected,
  onSelect,
}: {
  row: ForecastRow
  isFirst: boolean
  selected: boolean
  onSelect: () => void
}) {
  const { severity } = classifyForecastRow(row)
  const Icon = CONDITION_ICONS[conditionFor(row)]

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full flex-col gap-3 rounded-card bg-card p-5 text-left transition-colors",
        selected ? "ring-2 ring-forest-ink" : "hover:bg-ash-gray/40"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-xs font-medium tracking-wide text-graphite">{dayLabel(row.date, isFirst)}</p>
          <p className="text-sm text-pewter">
            {new Date(row.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </p>
        </div>
        <Icon className="size-7 text-forest-ink" aria-hidden="true" />
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-light text-charcoal">{row.temp_min_c ?? "--"}°</span>
        <span className="text-sm text-pewter">→</span>
        <span className="text-2xl font-medium text-charcoal">{row.temp_max_c ?? "--"}°</span>
      </div>

      <dl className="space-y-1.5 text-xs text-graphite">
        <div className="flex items-center gap-1.5">
          <CloudRain className="size-3.5" aria-hidden="true" />
          Rain: {row.rainfall_mm != null ? `${row.rainfall_mm.toFixed(1)}mm` : "Data unavailable"}
        </div>
        <div className="flex items-center gap-1.5">
          <Droplets className="size-3.5" aria-hidden="true" />
          Humidity: {row.rh_max_pct != null ? `${row.rh_max_pct}%` : "Data unavailable"}
        </div>
        <div className="flex items-center gap-1.5">
          <Wind className="size-3.5" aria-hidden="true" />
          Wind: {row.wind_max_kmh != null ? `${row.wind_max_kmh}km/h` : "Data unavailable"}
        </div>
      </dl>

      <RiskIndicator severity={severity} className="self-start" />
    </button>
  )
}
