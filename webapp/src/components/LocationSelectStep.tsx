import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ApiError, updateProfile } from "@/lib/api"
import { useAuth } from "@/lib/AuthProvider"
import { KHAMMAM_MANDALS, STATE, districtHasData, mandalHasData } from "@/lib/telanganaLocations"
import { useTelanganaGeoJson } from "@/lib/useTelanganaGeoJson"
import { cn } from "@/lib/utils"

/** Shown on Home when the user has no saved State/District/Block yet, or
 * when they choose "Change Location" after already having one. Real
 * district/mandal names only (see lib/telanganaLocations.ts) -- everywhere
 * without a real downscaled forecast is visibly disabled, not hidden or
 * faked. */
export function LocationSelectStep({
  initialDistrict = "",
  initialBlock = "",
  onDone,
}: {
  initialDistrict?: string
  initialBlock?: string
  /** Called once a location is saved, and also when "Cancel" is clicked
   * (only shown when there was already a saved location to go back to). */
  onDone?: () => void
}) {
  const { refreshUser } = useAuth()
  const geoQuery = useTelanganaGeoJson()
  const [district, setDistrict] = useState(initialDistrict)
  const [block, setBlock] = useState(initialBlock)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const districtNames = [...(geoQuery.data?.features.map((f) => f.properties.district) ?? [])].sort()

  const onSave = async () => {
    setError(null)
    setSaving(true)
    try {
      await updateProfile({ selected_state: STATE, selected_district: district, selected_block: block })
      await refreshUser()
      onDone?.()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your location. Check your connection and try again.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-5 rounded-hero-card bg-card p-8">
      <div>
        <h1 className="font-serif text-2xl font-medium text-charcoal">Where's your farm?</h1>
        <p className="mt-1 text-sm text-graphite">
          Select your location so FarmWise can show weather and advisories for your area.
        </p>
      </div>

      <div className="space-y-1.5">
        <Label>State</Label>
        <Select value={STATE} disabled>
          <SelectTrigger className="w-full">
            <SelectValue>{STATE}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={STATE}>{STATE}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>District</Label>
        <Select
          value={district}
          onValueChange={(v) => {
            if (v) {
              setDistrict(v)
              setBlock("")
            }
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select district" />
          </SelectTrigger>
          <SelectContent>
            {districtNames.map((name) => (
              <SelectItem key={name} value={name} disabled={!districtHasData(name)}>
                <span className={cn(!districtHasData(name) && "text-pewter")}>
                  {name} {!districtHasData(name) && "— No data yet"}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Block / Mandal</Label>
        <Select value={block} onValueChange={(v) => v && setBlock(v)} disabled={!districtHasData(district)}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder={districtHasData(district) ? "Select block" : "—"} />
          </SelectTrigger>
          <SelectContent>
            {KHAMMAM_MANDALS.map((name) => (
              <SelectItem key={name} value={name} disabled={!mandalHasData(name)}>
                <span className={cn(!mandalHasData(name) && "text-pewter")}>
                  {name} {!mandalHasData(name) && "— No data yet"}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {error && (
        <p className="rounded-xl bg-status-critical-bg px-3 py-2 text-sm text-status-critical">{error}</p>
      )}

      <div className="flex gap-3">
        {onDone && (
          <Button type="button" variant="outline" className="flex-1" disabled={saving} onClick={onDone}>
            Cancel
          </Button>
        )}
        <Button className="flex-1" disabled={!district || !block || saving} onClick={onSave}>
          {saving ? "..." : "Continue"}
        </Button>
      </div>
    </div>
  )
}
