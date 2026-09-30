import { Leaf } from "lucide-react"

import { RiskIndicator } from "@/components/RiskIndicator"
import { Button } from "@/components/ui/button"
import type { CropAdvisory, Crop } from "@/lib/api"
import { SEVERITY_STYLES } from "@/lib/advisory"
import { cn } from "@/lib/utils"

const PASTEL_TONES = ["bg-sky-card", "bg-peach-card", "bg-sage-card", "bg-ash-gray"] as const

export function CropCard({
  crop,
  farmName,
  toneIndex = 0,
  advisory,
  onEdit,
  onDelete,
}: {
  crop: Crop
  farmName?: string
  toneIndex?: number
  advisory?: CropAdvisory
  onEdit?: () => void
  onDelete?: () => void
}) {
  const tone = PASTEL_TONES[toneIndex % PASTEL_TONES.length]

  return (
    <div className={cn("rounded-card p-6", tone)}>
      <div className="mb-3 flex items-center gap-2">
        <Leaf className="size-4 text-forest-ink" aria-hidden="true" />
        <h3 className="font-serif text-lg font-medium text-charcoal">{crop.crop_name}</h3>
      </div>
      <dl className="space-y-1 text-sm text-graphite">
        {crop.variety && (
          <div className="flex justify-between">
            <dt>Variety</dt>
            <dd>{crop.variety}</dd>
          </div>
        )}
        <div className="flex justify-between">
          <dt>Stage</dt>
          <dd className="font-medium text-forest-ink">{crop.stage}</dd>
        </div>
        {farmName && (
          <div className="flex justify-between">
            <dt>Farm</dt>
            <dd>{farmName}</dd>
          </div>
        )}
        {crop.area_value != null && (
          <div className="flex justify-between">
            <dt>Area</dt>
            <dd>
              {crop.area_value} {crop.area_unit}
            </dd>
          </div>
        )}
      </dl>

      {advisory && advisory.severity !== "safe" && (
        <div className={cn("mt-4 rounded-xl bg-card p-3 text-sm", SEVERITY_STYLES[advisory.severity].text)}>
          <div className="mb-1 flex items-center justify-between">
            <span className="font-medium text-charcoal">{advisory.what}</span>
            <RiskIndicator severity={advisory.severity} />
          </div>
          <p>{advisory.action}</p>
        </div>
      )}

      {(onEdit || onDelete) && (
        <div className="mt-4 flex gap-2">
          {onEdit && (
            <Button variant="outline" size="sm" className="flex-1" onClick={onEdit}>
              🔄 Change Crop
            </Button>
          )}
          {onDelete && (
            <Button variant="outline" size="sm" onClick={onDelete}>
              🗑️
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
