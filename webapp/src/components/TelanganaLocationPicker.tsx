import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getGps } from "@/lib/api"
import { KHAMMAM_MANDALS, MANDAL_WITH_DATA, STATE, districtHasData, mandalHasData } from "@/lib/telanganaLocations"
import { useTelanganaGeoJson } from "@/lib/useTelanganaGeoJson"
import { cn } from "@/lib/utils"

export interface TelanganaSelection {
  district: string
  mandal: string
  panchayat: string
}

export function TelanganaLocationPicker({ onChange }: { onChange?: (selection: TelanganaSelection) => void }) {
  const geoQuery = useTelanganaGeoJson()
  const gpsQuery = useQuery({ queryKey: ["gps"], queryFn: getGps })

  const [district, setDistrict] = useState("")
  const [mandal, setMandal] = useState("")
  const [panchayat, setPanchayat] = useState("")

  const districtNames = [...(geoQuery.data?.features.map((f) => f.properties.district) ?? [])].sort()

  const emit = (next: Partial<TelanganaSelection>) => {
    const merged = { district, mandal, panchayat, ...next }
    setDistrict(merged.district)
    setMandal(merged.mandal)
    setPanchayat(merged.panchayat)
    onChange?.(merged)
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
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
        <Select value={district} onValueChange={(v) => v && emit({ district: v, mandal: "", panchayat: "" })}>
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
        <Select
          value={mandal}
          onValueChange={(v) => v && emit({ mandal: v, panchayat: "" })}
          disabled={!districtHasData(district)}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder={districtHasData(district) ? "Select mandal" : "—"} />
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

      <div className="space-y-1.5">
        <Label>Gram Panchayat</Label>
        <Select
          value={panchayat}
          onValueChange={(v) => v && emit({ panchayat: v })}
          disabled={mandal !== MANDAL_WITH_DATA}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder={mandal === MANDAL_WITH_DATA ? "Select Gram Panchayat" : "—"} />
          </SelectTrigger>
          <SelectContent>
            {(gpsQuery.data ?? []).map((gp) => (
              <SelectItem key={gp.gram_panchayat} value={gp.gram_panchayat}>
                {gp.gram_panchayat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
