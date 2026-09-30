import { CloudRain, Droplets, Thermometer, Wind } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ForecastRow } from "@/lib/api"
import { computeFeelsLikeC } from "@/lib/weather"

export function WeatherCard({ row }: { row: ForecastRow }) {
  const { t } = useTranslation()
  const feelsLike =
    row.temp_max_c != null && row.rh_max_pct != null
      ? computeFeelsLikeC(row.temp_max_c, row.rh_max_pct)
      : null

  return (
    <Card className="rounded-card p-0 ring-0">
      <CardHeader className="rounded-t-card bg-forest-ink px-6 py-5 text-white">
        <CardTitle className="font-serif text-2xl font-normal text-white">
          {row.gram_panchayat}
        </CardTitle>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-4xl font-light">{row.temp_max_c ?? "--"}°</span>
          {feelsLike != null && (
            <span className="text-sm text-white/70">Feels like {feelsLike}°</span>
          )}
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 px-6 py-5 sm:grid-cols-4">
        <Stat icon={Thermometer} label={t("weather.temperature")} value={`${row.temp_min_c ?? "--"}–${row.temp_max_c ?? "--"}°`} />
        <Stat icon={Droplets} label={t("weather.humidity")} value={row.rh_max_pct != null ? `${row.rh_max_pct}%` : "--"} />
        <Stat icon={Wind} label={t("weather.wind")} value={row.wind_max_kmh != null ? `${row.wind_max_kmh} km/h` : "--"} />
        <Stat icon={CloudRain} label={t("weather.rainfall")} value={row.rainfall_mm != null ? `${row.rainfall_mm.toFixed(1)} mm` : "--"} />
      </CardContent>
    </Card>
  )
}

function Stat({ icon: Icon, label, value }: { icon: typeof Thermometer; label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-xs text-pewter">
        <Icon className="size-3.5" aria-hidden="true" />
        {label}
      </div>
      <span className="text-sm font-medium text-charcoal">{value}</span>
    </div>
  )
}
