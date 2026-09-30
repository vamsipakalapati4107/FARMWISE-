import { useTranslation } from "react-i18next"

import { RiskIndicator } from "@/components/RiskIndicator"
import { classifyForecastRow } from "@/lib/advisory"
import type { ForecastRow } from "@/lib/api"

/** Named WeeklyForecast per the component list, but shows the real 5-day
 * horizon we actually have -- see DESIGN.md / the "Data horizon" decision. */
export function WeeklyForecast({ rows }: { rows: ForecastRow[] }) {
  const { t } = useTranslation()

  return (
    <div className="rounded-card bg-card p-6">
      <h3 className="mb-4 font-serif text-lg font-medium text-charcoal">{t("weather.forecast5day")}</h3>
      <div className="divide-y divide-moss/40">
        {rows.map((row) => {
          const { severity } = classifyForecastRow(row)
          return (
            <div key={row.date} className="flex items-center justify-between gap-3 py-3">
              <span className="w-24 text-sm text-graphite">
                {new Date(row.date).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}
              </span>
              <span className="flex-1 text-sm text-pewter">
                {row.temp_min_c ?? "--"}° – {row.temp_max_c ?? "--"}°
              </span>
              <span className="w-20 text-right text-sm text-status-info">
                {row.rainfall_mm != null ? `${row.rainfall_mm.toFixed(1)} mm` : "--"}
              </span>
              <RiskIndicator severity={severity} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
