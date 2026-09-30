import { RiskIndicator } from "@/components/RiskIndicator"
import type { AdvisoryDetail } from "@/lib/advisory"
import { SEVERITY_STYLES } from "@/lib/advisory"
import { cn } from "@/lib/utils"

export interface AdvisoryCardProps extends AdvisoryDetail {
  gramPanchayat?: string
  dateLabel: string
  prominent?: boolean
}

export function AdvisoryCard({
  severity,
  what,
  why,
  action,
  gramPanchayat,
  dateLabel,
  prominent = false,
}: AdvisoryCardProps) {
  const style = SEVERITY_STYLES[severity]

  return (
    <div
      className={cn(
        "rounded-card border-l-4 bg-card p-6",
        style.border,
        prominent && "ring-2 ring-forest-ink/20"
      )}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="text-sm text-pewter">
          {gramPanchayat && <span className="font-medium text-charcoal">{gramPanchayat}</span>}
          {gramPanchayat && " · "}
          {dateLabel}
        </div>
        <RiskIndicator severity={severity} />
      </div>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="font-medium text-charcoal">What</dt>
          <dd className="text-graphite">{what}</dd>
        </div>
        <div>
          <dt className="font-medium text-charcoal">Why it matters</dt>
          <dd className="text-graphite">{why}</dd>
        </div>
        <div>
          <dt className="font-medium text-charcoal">Recommended action</dt>
          <dd className={cn("font-medium", style.text)}>{action}</dd>
        </div>
      </dl>
    </div>
  )
}
