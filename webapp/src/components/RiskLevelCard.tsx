import { MLSourceBadge } from "@/components/MLSourceBadge"
import type { MlClassification } from "@/lib/api"
import { cn } from "@/lib/utils"

const LEVEL_STYLES: Record<string, string> = {
  LOW: "bg-status-safe-bg text-status-safe",
  MEDIUM: "bg-status-warning-bg text-status-warning",
  HIGH: "bg-status-critical-bg text-status-critical",
}

export function RiskLevelCard({
  title,
  level,
  why,
  classification,
  unavailableReason,
}: {
  title: string
  level: "LOW" | "MEDIUM" | "HIGH" | null
  why: string
  classification?: MlClassification
  unavailableReason?: string
}) {
  return (
    <div className="rounded-card bg-card p-5">
      <h3 className="mb-2 text-sm font-medium text-graphite">{title}</h3>
      {level ? (
        <>
          <span className={cn("inline-block rounded-full px-3 py-1 text-sm font-medium", LEVEL_STYLES[level])}>
            {level}
          </span>
          <p className="mt-2 text-xs text-graphite">{why}</p>
        </>
      ) : (
        <>
          <span className="inline-block rounded-full bg-ash-gray px-3 py-1 text-sm font-medium text-pewter">
            Not available
          </span>
          <p className="mt-2 text-xs text-graphite">{unavailableReason ?? why}</p>
        </>
      )}
      {classification && (
        <div className="mt-3">
          <MLSourceBadge classification={classification} />
        </div>
      )}
    </div>
  )
}
