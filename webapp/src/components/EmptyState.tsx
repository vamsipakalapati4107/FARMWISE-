import type { LucideIcon } from "lucide-react"
import { Inbox } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"

export function EmptyState({
  icon: Icon = Inbox,
  message,
  actionLabel,
  onAction,
}: {
  icon?: LucideIcon
  message?: string
  actionLabel?: string
  onAction?: () => void
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-moss bg-ash-gray/50 px-6 py-12 text-center">
      <Icon className="size-6 text-pewter" aria-hidden="true" />
      <p className="text-sm text-pewter">{message ?? t("common.empty")}</p>
      {actionLabel && onAction && (
        <Button size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
