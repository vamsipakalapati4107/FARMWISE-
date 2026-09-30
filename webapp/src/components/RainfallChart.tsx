import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import type { ForecastRow } from "@/lib/api"

export function RainfallChart({ rows }: { rows: ForecastRow[] }) {
  const data = rows.map((row) => ({
    date: new Date(row.date).toLocaleDateString(undefined, { day: "numeric", month: "short" }),
    rainfall: row.rainfall_mm ?? 0,
  }))

  return (
    <div className="h-56 rounded-card bg-card p-6">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-moss)" opacity={0.4} vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--color-pewter)" }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--color-pewter)" }}
            axisLine={false}
            tickLine={false}
            label={{ value: "mm", angle: -90, position: "insideLeft", fontSize: 11, fill: "var(--color-pewter)" }}
          />
          <Tooltip formatter={(value) => [`${Number(value).toFixed(1)} mm`, "Rainfall"]} />
          <Bar dataKey="rainfall" fill="var(--color-status-info)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
