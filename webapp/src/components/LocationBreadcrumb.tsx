import { MapPin } from "lucide-react"

export function LocationBreadcrumb({
  village,
  gramPanchayat,
  block,
  district,
  state,
}: {
  village?: string | null
  gramPanchayat: string
  block: string
  district: string
  state: string
}) {
  const parts = [village, gramPanchayat, block, district, state].filter(Boolean)
  return (
    <div className="flex items-center gap-1.5 text-sm text-graphite">
      <MapPin className="size-4 text-forest-ink" aria-hidden="true" />
      <span>{parts.join(" · ")}</span>
    </div>
  )
}
