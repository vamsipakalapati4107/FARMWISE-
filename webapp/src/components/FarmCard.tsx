import { Droplets, MapPin, MapPinOff, Sprout } from "lucide-react"
import { Link } from "react-router-dom"

import { RiskIndicator } from "@/components/RiskIndicator"
import { Button } from "@/components/ui/button"
import type { Severity } from "@/lib/advisory"
import type { Farm } from "@/lib/api"
import { cn } from "@/lib/utils"

export function FarmCard({
  farm,
  onEdit,
  onDelete,
  viewHref,
  cropCondition,
  warningsCount,
}: {
  farm: Farm
  onEdit?: () => void
  onDelete?: () => void
  viewHref?: string
  /** Worst-case severity across the farm's crops (from real crop-advisory
   * data) -- undefined when there's no crop/advisory data to summarize,
   * never a guessed default. */
  cropCondition?: Severity
  warningsCount?: number
}) {
  const hasCoordinates = farm.latitude != null && farm.longitude != null

  return (
    <div className="rounded-card bg-card p-6">
      <div className="mb-3 flex items-start justify-between gap-2">
        <h3 className="font-serif text-lg font-medium text-charcoal">🌾 {farm.name}</h3>
        <div className="flex gap-2">
          {onEdit && (
            <Button variant="outline" size="sm" onClick={onEdit}>
              ✏️ Edit
            </Button>
          )}
          {onDelete && (
            <Button variant="outline" size="sm" onClick={onDelete}>
              🗑️ Delete
            </Button>
          )}
        </div>
      </div>

      {(cropCondition || (warningsCount ?? 0) > 0) && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {cropCondition && <RiskIndicator severity={cropCondition} />}
          {(warningsCount ?? 0) > 0 && (
            <span className="rounded-full bg-status-warning-bg px-3 py-1 text-xs font-medium text-status-warning">
              ⚠️ {warningsCount} Warning{warningsCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      )}
      <div className="space-y-2 text-sm text-graphite">
        <div className="flex items-center gap-2">
          <MapPin className="size-4 text-pewter" aria-hidden="true" />
          {[farm.village, farm.gram_panchayat, farm.block, farm.district, farm.state].filter(Boolean).join(", ")}
        </div>

        {/* Phase 0.5: plot-precision location status -- never invents
         * coordinates for farms that don't have them. */}
        <div className="flex items-center gap-2">
          {hasCoordinates ? (
            <>
              <MapPin className="size-4 text-status-safe" aria-hidden="true" />
              <span>
                Plot location set ({farm.latitude!.toFixed(4)}, {farm.longitude!.toFixed(4)})
              </span>
            </>
          ) : (
            <>
              <MapPinOff className="size-4 text-status-warning" aria-hidden="true" />
              <span className={cn("italic")}>Location not configured</span>
            </>
          )}
        </div>

        {farm.area_value != null && (
          <div className="flex items-center gap-2">
            <Sprout className="size-4 text-pewter" aria-hidden="true" />
            {farm.area_value} {farm.area_unit}
            {farm.soil_type && ` · ${farm.soil_type} soil`}
          </div>
        )}
        {farm.irrigation && (
          <div className="flex items-center gap-2">
            <Droplets className="size-4 text-pewter" aria-hidden="true" />
            {farm.irrigation}
          </div>
        )}
      </div>

      {viewHref && (
        <Link
          to={viewHref}
          className="mt-4 inline-block rounded-nav-pill bg-forest-ink px-4 py-2 text-sm font-medium text-white hover:bg-forest-ink/90"
        >
          View Farm →
        </Link>
      )}
    </div>
  )
}
