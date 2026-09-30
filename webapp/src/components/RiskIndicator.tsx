import { AlertTriangle, CheckCircle2, TriangleAlert } from "lucide-react"
import { useTranslation } from "react-i18next"

import type { Severity } from "@/lib/advisory"
import { SEVERITY_STYLES } from "@/lib/advisory"
import { cn } from "@/lib/utils"

const ICONS = {
  critical: AlertTriangle,
  warning: TriangleAlert,
  safe: CheckCircle2,
} as const

export function RiskIndicator({ severity, className }: { severity: Severity; className?: string }) {
  const { t } = useTranslation()
  const style = SEVERITY_STYLES[severity]
  const Icon = ICONS[severity]

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
        style.bg,
        style.text,
        className
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {t(`advisory_severity.${severity}`)}
    </span>
  )
}
