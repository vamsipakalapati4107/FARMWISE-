import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"

export function LoadingState({ label }: { label?: string }) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-pewter">
      <Loader2 className="size-6 animate-spin" aria-hidden="true" />
      <p className="text-sm">{label ?? t("common.loading")}</p>
    </div>
  )
}
