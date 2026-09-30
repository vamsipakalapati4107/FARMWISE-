import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { CropSelector, type CropSelectorValue } from "@/components/CropSelector"
import { LanguageSelector } from "@/components/LanguageSelector"
import { EMPTY_LOCATION, LocationSelector, type LocationValue } from "@/components/LocationSelector"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import * as api from "@/lib/api"
import { cn } from "@/lib/utils"

const STEP_LABELS = ["Location", "Farm", "Crop", "Preferences"]

const IRRIGATION_OPTIONS = ["Rainfed", "Borewell", "Canal", "Drip", "Sprinkler"]
const SOIL_OPTIONS = ["Black soil", "Red soil", "Sandy loam", "Clay loam", "Alluvial"]

export function Onboarding() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [submitting, setSubmitting] = useState(false)

  const [location, setLocation] = useState<LocationValue>(EMPTY_LOCATION)
  const [farm, setFarm] = useState({ name: "", areaValue: "", areaUnit: "acre", irrigation: "", soilType: "" })
  const [crop, setCrop] = useState<CropSelectorValue>({ cropName: "", variety: "", stage: "" })
  const [sowingDate, setSowingDate] = useState("")
  const [notifications, setNotifications] = useState(true)
  const [units, setUnits] = useState<"metric" | "imperial">("metric")

  const canContinue = [
    !!location.gramPanchayat,
    !!farm.name,
    !!crop.cropName,
    true, // preferences step has sensible defaults
  ][step]

  const onFinish = async () => {
    setSubmitting(true)
    try {
      const createdFarm = await api.createFarm({
        name: farm.name,
        gram_panchayat: location.gramPanchayat,
        state: location.state || "Telangana",
        district: location.district || "Khammam",
        block: location.block || "Sathupally",
        village: location.village || null,
        area_value: farm.areaValue ? Number(farm.areaValue) : null,
        area_unit: farm.areaUnit,
        irrigation: farm.irrigation || null,
        soil_type: farm.soilType || null,
      })

      await api.createCrop({
        farm_id: createdFarm.id,
        crop_name: crop.cropName,
        variety: crop.variety || null,
        stage: crop.stage,
        sowing_date: sowingDate || null,
        area_value: null,
        area_unit: "acre",
      })

      localStorage.setItem("selected_gp", location.gramPanchayat)
      localStorage.setItem("notification_prefs", JSON.stringify({ enabled: notifications }))
      localStorage.setItem("units", units)

      navigate("/dashboard")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bone px-4 py-10">
      <div className="w-full max-w-lg rounded-hero-card bg-card p-8">
        <div className="mb-8 flex items-center justify-center gap-2">
          {STEP_LABELS.map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex size-8 items-center justify-center rounded-full text-xs font-medium",
                  i === step
                    ? "bg-forest-ink text-white"
                    : i < step
                      ? "bg-sage-card text-forest-ink"
                      : "bg-ash-gray text-pewter"
                )}
              >
                {i + 1}
              </span>
              {i < STEP_LABELS.length - 1 && <span className="h-px w-6 bg-moss" />}
            </div>
          ))}
        </div>
        <p className="mb-6 text-center text-sm font-medium text-graphite">{STEP_LABELS[step]}</p>

        {step === 0 && <LocationSelector value={location} onChange={setLocation} />}

        {step === 1 && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Farm name</Label>
              <Input
                value={farm.name}
                onChange={(e) => setFarm({ ...farm, name: e.target.value })}
                placeholder="My Cotton Field"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Farm area</Label>
                <Input
                  type="number"
                  value={farm.areaValue}
                  onChange={(e) => setFarm({ ...farm, areaValue: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Unit</Label>
                <Select value={farm.areaUnit} onValueChange={(v) => v && setFarm({ ...farm, areaUnit: v })}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="acre">Acre</SelectItem>
                    <SelectItem value="hectare">Hectare</SelectItem>
                    <SelectItem value="guntha">Guntha</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Irrigation availability</Label>
              <Select value={farm.irrigation} onValueChange={(v) => v && setFarm({ ...farm, irrigation: v })}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select irrigation type" />
                </SelectTrigger>
                <SelectContent>
                  {IRRIGATION_OPTIONS.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Soil type (if known)</Label>
              <Select value={farm.soilType} onValueChange={(v) => v && setFarm({ ...farm, soilType: v })}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select soil type" />
                </SelectTrigger>
                <SelectContent>
                  {SOIL_OPTIONS.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <CropSelector value={crop} onChange={setCrop} />
            <div className="space-y-1.5">
              <Label>Sowing / planting date</Label>
              <Input type="date" value={sowingDate} onChange={(e) => setSowingDate(e.target.value)} />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <div className="space-y-1.5">
              <Label>Language</Label>
              <LanguageSelector />
            </div>
            <div className="space-y-1.5">
              <Label>Preferred units</Label>
              <Select value={units} onValueChange={(v) => v && setUnits(v as "metric" | "imperial")}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="metric">Metric (°C, mm, km/h)</SelectItem>
                  <SelectItem value="imperial">Imperial (°F, in, mph)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <label className="flex items-center gap-2 text-sm text-graphite">
              <Checkbox checked={notifications} onCheckedChange={(c) => setNotifications(c === true)} />
              Send me weather alerts and advisory notifications
            </label>
          </div>
        )}

        <div className="mt-8 flex justify-between gap-3">
          <Button variant="outline" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
            Back
          </Button>
          {step < STEP_LABELS.length - 1 ? (
            <Button disabled={!canContinue} onClick={() => setStep((s) => s + 1)}>
              Continue
            </Button>
          ) : (
            <Button disabled={submitting} onClick={onFinish}>
              {submitting ? "..." : t("common.save")}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
