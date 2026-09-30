import type { ReactNode } from "react"
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import type { ForecastRow } from "@/lib/api"

/** The 5-day GP forecast horizon is the finest real trend data available for
 * rainfall/humidity/wind (only temperature has a true hourly curve, and it's
 * a deterministic estimate -- see HourlyForecast). "Today's Outlook" here
 * means the outlook over the real forecast window, not a fabricated
 * hour-by-hour breakdown for variables that don't have one. */
function ChartCard({ title, children, empty }: { title: string; children: ReactNode; empty?: boolean }) {
  return (
    <div className="rounded-card bg-card p-5">
      <h3 className="mb-3 text-sm font-medium text-graphite">{title}</h3>
      {empty ? (
        <div className="flex h-40 items-center justify-center text-sm italic text-pewter">Data unavailable</div>
      ) : (
        <div className="h-40">{children}</div>
      )}
    </div>
  )
}

const axisProps = {
  tick: { fontSize: 10, fill: "var(--color-pewter)" },
  axisLine: false,
  tickLine: false,
} as const

export function TodayOutlookCharts({ rows }: { rows: ForecastRow[] }) {
  const data = rows.map((row) => ({
    date: new Date(row.date).toLocaleDateString(undefined, { weekday: "short" }),
    temp_max: row.temp_max_c,
    temp_min: row.temp_min_c,
    rainfall: row.rainfall_mm,
    humidity: row.rh_max_pct,
    wind: row.wind_max_kmh,
  }))

  const hasTemp = data.some((d) => d.temp_max != null)
  const hasRain = data.some((d) => d.rainfall != null)
  const hasHumidity = data.some((d) => d.humidity != null)
  const hasWind = data.some((d) => d.wind != null)

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <ChartCard title="Temperature trend" empty={!hasTemp}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} />
            <XAxis dataKey="date" {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip formatter={(v) => [`${v}°C`, ""]} />
            <Line type="monotone" dataKey="temp_max" name="Max" stroke="var(--color-status-critical)" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="temp_min" name="Min" stroke="var(--color-status-info)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Rainfall / precipitation" empty={!hasRain}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} vertical={false} />
            <XAxis dataKey="date" {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip formatter={(v) => [`${Number(v).toFixed(1)}mm`, "Rainfall"]} />
            <Bar dataKey="rainfall" fill="var(--color-status-info)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Humidity trend" empty={!hasHumidity}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} />
            <XAxis dataKey="date" {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip formatter={(v) => [`${v}%`, "Humidity"]} />
            <Line type="monotone" dataKey="humidity" stroke="var(--color-forest-ink)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Wind speed trend" empty={!hasWind}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} />
            <XAxis dataKey="date" {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip formatter={(v) => [`${v}km/h`, "Wind"]} />
            <Line type="monotone" dataKey="wind" stroke="var(--color-status-warning)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}
