import { AdvisoryCard } from "@/components/AdvisoryCard"
import { EmptyState } from "@/components/EmptyState"
import { buildAdvisoryDetail } from "@/lib/advisory"
import type { Alert, ForecastRow } from "@/lib/api"

/** Renders one AdvisoryCard per forecast row. Prefers the real backend
 * alert for a date when one exists (src/routers/alerts.py); falls back to
 * the client-side classification for "safe" days, which the alerts
 * endpoint intentionally omits (normal operations isn't an alert). */
export function AdvisoryList({
  rows,
  alerts = [],
  showGpName = false,
}: {
  rows: ForecastRow[]
  alerts?: Alert[]
  showGpName?: boolean
}) {
  if (rows.length === 0) return <EmptyState message="No advisories for this selection." />

  const alertsByKey = new Map(alerts.map((a) => [`${a.gram_panchayat}-${a.date}`, a]))

  return (
    <div className="space-y-4">
      {rows.map((row) => {
        const alert = alertsByKey.get(`${row.gram_panchayat}-${row.date}`)
        const detail = alert
          ? { severity: alert.severity, what: alert.title, why: alert.description, action: alert.action }
          : buildAdvisoryDetail(row)

        return (
          <AdvisoryCard
            key={`${row.gram_panchayat}-${row.date}`}
            {...detail}
            gramPanchayat={showGpName ? row.gram_panchayat : undefined}
            dateLabel={new Date(row.date).toLocaleDateString(undefined, {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          />
        )
      })}
    </div>
  )
}
