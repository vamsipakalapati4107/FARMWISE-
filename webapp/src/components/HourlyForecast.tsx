import { useTranslation } from "react-i18next"
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import type { EstimatedHourPoint } from "@/lib/api"

export function HourlyForecast({ points }: { points: EstimatedHourPoint[] }) {
  const { t } = useTranslation()

  return (
    <div className="rounded-card bg-card p-6">
      <div className="mb-1 flex items-center justify-between">
        <h3 className="font-serif text-lg font-medium text-charcoal">{t("weather.hourlyEstimated")}</h3>
        <span className="rounded-full bg-status-info-bg px-3 py-1 text-xs font-medium text-status-info">
          Estimated
        </span>
      </div>
      <p className="mb-4 text-xs text-pewter">{t("weather.estimatedNotice")}</p>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ left: -20, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} />
            <XAxis
              dataKey="hour"
              tickFormatter={(h: number) => `${h}:00`}
              interval={3}
              tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis tick={{ fontSize: 11, fill: "var(--color-pewter)" }} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={(value) => [`${value}°`, "Estimated temp"]}
              labelFormatter={(h) => `${h}:00`}
            />
            <Line type="monotone" dataKey="temp_c" stroke="var(--color-forest-ink)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
