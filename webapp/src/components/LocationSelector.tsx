import { useQuery } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"

import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getBlocks, getDistricts, getPanchayats, getStates, getVillages } from "@/lib/api"

export interface LocationValue {
  state: string
  district: string
  block: string
  gramPanchayat: string
  village: string
}

export const EMPTY_LOCATION: LocationValue = { state: "", district: "", block: "", gramPanchayat: "", village: "" }

export function LocationSelector({
  value,
  onChange,
}: {
  value: LocationValue
  onChange: (value: LocationValue) => void
}) {
  const { t } = useTranslation()

  const { data: states = [] } = useQuery({ queryKey: ["locations", "states"], queryFn: getStates })
  const { data: districts = [] } = useQuery({
    queryKey: ["locations", "districts", value.state],
    queryFn: () => getDistricts(value.state),
    enabled: !!value.state,
  })
  const { data: blocks = [] } = useQuery({
    queryKey: ["locations", "blocks", value.state, value.district],
    queryFn: () => getBlocks(value.state, value.district),
    enabled: !!value.state && !!value.district,
  })
  const { data: panchayats = [] } = useQuery({
    queryKey: ["locations", "panchayats", value.state, value.district, value.block],
    queryFn: () => getPanchayats(value.state, value.district, value.block),
    enabled: !!value.state && !!value.district && !!value.block,
  })
  const { data: villages = [] } = useQuery({
    queryKey: ["locations", "villages", value.state, value.district, value.block, value.gramPanchayat],
    queryFn: () => getVillages(value.state, value.district, value.block, value.gramPanchayat),
    enabled: !!value.state && !!value.district && !!value.block && !!value.gramPanchayat,
  })

  return (
    <div className="space-y-4">
      <LevelSelect
        label={t("location.state")}
        options={states}
        selected={value.state}
        onSelect={(state) => onChange({ ...EMPTY_LOCATION, state })}
      />
      <LevelSelect
        label={t("location.district")}
        options={districts}
        selected={value.district}
        disabled={!value.state}
        onSelect={(district) => onChange({ ...value, district, block: "", gramPanchayat: "", village: "" })}
      />
      <LevelSelect
        label={t("location.block")}
        options={blocks}
        selected={value.block}
        disabled={!value.district}
        onSelect={(block) => onChange({ ...value, block, gramPanchayat: "", village: "" })}
      />
      <LevelSelect
        label={t("location.panchayat")}
        options={panchayats}
        selected={value.gramPanchayat}
        disabled={!value.block}
        onSelect={(gramPanchayat) => onChange({ ...value, gramPanchayat, village: "" })}
      />
      <LevelSelect
        label={t("location.village")}
        options={villages}
        selected={value.village}
        disabled={!value.gramPanchayat}
        onSelect={(village) => onChange({ ...value, village })}
      />
    </div>
  )
}

function LevelSelect({
  label,
  options,
  selected,
  disabled,
  onSelect,
}: {
  label: string
  options: string[]
  selected: string
  disabled?: boolean
  onSelect: (value: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Select
        value={selected}
        onValueChange={(value) => value && onSelect(value)}
        disabled={disabled || options.length === 0}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder={disabled ? "—" : `Select ${label.toLowerCase()}`} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
