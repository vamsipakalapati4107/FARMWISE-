import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query"
import { MapPin, MapPinOff, Plus, Sparkles, Trash2 } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router-dom"

import { CropCard } from "@/components/CropCard"
import { CropSelector, type CropSelectorValue } from "@/components/CropSelector"
import { EmptyState } from "@/components/EmptyState"
import { ErrorState } from "@/components/ErrorState"
import { FarmCard } from "@/components/FarmCard"
import { FarmMap } from "@/components/FarmMap"
import { EMPTY_LOCATION, LocationSelector, type LocationValue } from "@/components/LocationSelector"
import { LoadingState } from "@/components/LoadingState"
import { MLSourceBadge } from "@/components/MLSourceBadge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { Severity } from "@/lib/advisory"
import * as api from "@/lib/api"
import type { Crop } from "@/lib/api"

const SEVERITY_ORDER: Record<Severity, number> = { critical: 3, warning: 2, safe: 1 }

function worstSeverity(advisories: api.CropAdvisory[]): Severity | undefined {
  if (advisories.length === 0) return undefined
  return advisories.reduce<Severity>((worst, a) => (SEVERITY_ORDER[a.severity] > SEVERITY_ORDER[worst] ? a.severity : worst), "safe")
}

export function Farm() {
  const queryClient = useQueryClient()
  const {
    data: farms,
    isLoading: farmsLoading,
    isError: farmsError,
  } = useQuery({ queryKey: ["farms"], queryFn: api.listFarms })
  const { data: crops } = useQuery({ queryKey: ["crops"], queryFn: () => api.listCrops() })

  const advisoryQueries = useQueries({
    queries: (farms ?? []).map((farm) => ({
      queryKey: ["crop-advisory", farm.id],
      queryFn: () => api.getCropAdvisoryForFarm(farm.id),
    })),
  })
  const plotQueries = useQueries({
    queries: (farms ?? []).map((farm) => ({
      queryKey: ["plots", farm.id],
      queryFn: () => api.listPlots(farm.id),
    })),
  })
  const farmAlertQueries = useQueries({
    queries: (farms ?? []).map((farm) => ({
      queryKey: ["farm-alerts", farm.id],
      queryFn: () => api.getFarmAlerts(farm.id),
    })),
  })

  const [addFarmOpen, setAddFarmOpen] = useState(false)
  const [addCropFarmId, setAddCropFarmId] = useState<string | null>(null)
  const [addPlotFarmId, setAddPlotFarmId] = useState<string | null>(null)
  const [editFarm, setEditFarm] = useState<api.Farm | null>(null)
  const [deleteFarm, setDeleteFarm] = useState<api.Farm | null>(null)
  const [changeCropOf, setChangeCropOf] = useState<Crop | null>(null)
  const [deleteCrop, setDeleteCrop] = useState<Crop | null>(null)
  const [deletePlot, setDeletePlot] = useState<api.Plot | null>(null)

  if (farmsLoading) return <LoadingState />
  if (farmsError) return <ErrorState />

  const advisoryByCropId = new Map<string, api.CropAdvisory>()
  const advisoriesByFarm = new Map<string, api.CropAdvisory[]>()
  ;(farms ?? []).forEach((farm, i) => {
    const data = advisoryQueries[i]?.data ?? []
    advisoriesByFarm.set(farm.id, data)
    for (const advisory of data) advisoryByCropId.set(advisory.crop_id, advisory)
  })

  const cropsByFarm = new Map<string, Crop[]>()
  for (const crop of crops ?? []) {
    cropsByFarm.set(crop.farm_id, [...(cropsByFarm.get(crop.farm_id) ?? []), crop])
  }

  const plotsByFarm = new Map<string, api.Plot[]>()
  const activeWarningsByFarm = new Map<string, number>()
  ;(farms ?? []).forEach((farm, i) => {
    plotsByFarm.set(farm.id, plotQueries[i]?.data ?? [])
    const alerts = farmAlertQueries[i]?.data ?? []
    activeWarningsByFarm.set(farm.id, alerts.filter((a) => a.status !== "resolved" && a.status !== "expired").length)
  })

  const refreshFarms = () => queryClient.invalidateQueries({ queryKey: ["farms"] })
  const refreshCrops = () => {
    queryClient.invalidateQueries({ queryKey: ["crops"] })
    queryClient.invalidateQueries({ queryKey: ["crop-advisory"] })
  }
  const refreshPlots = () => queryClient.invalidateQueries({ queryKey: ["plots"] })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-serif text-2xl font-medium text-charcoal">🌾 My Farms</h1>
        <Dialog open={addFarmOpen} onOpenChange={setAddFarmOpen}>
          <DialogTrigger
            render={
              <Button size="sm">
                <Plus className="size-4" /> Add Farm
              </Button>
            }
          />
          <AddFarmDialog
            onCreated={() => {
              setAddFarmOpen(false)
              refreshFarms()
            }}
          />
        </Dialog>
      </div>

      {!farms || farms.length === 0 ? (
        <EmptyState message="No farms added yet." actionLabel="Add Farm" onAction={() => setAddFarmOpen(true)} />
      ) : (
        <div className="space-y-8">
          <div>
            <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🗺️ Farm Map</h2>
            <FarmMap />
          </div>

          {farms.map((farm) => (
            <div key={farm.id} className="space-y-4">
              <FarmCard
                farm={farm}
                viewHref={`/farms/${farm.id}`}
                cropCondition={worstSeverity(advisoriesByFarm.get(farm.id) ?? [])}
                warningsCount={activeWarningsByFarm.get(farm.id)}
                onEdit={() => setEditFarm(farm)}
                onDelete={() => setDeleteFarm(farm)}
              />

              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium text-graphite">📐 Plots</h2>
                <Dialog open={addPlotFarmId === farm.id} onOpenChange={(open) => setAddPlotFarmId(open ? farm.id : null)}>
                  <DialogTrigger
                    render={
                      <Button variant="outline" size="sm">
                        <Plus className="size-4" /> Add Plot
                      </Button>
                    }
                  />
                  <AddPlotDialog
                    farmId={farm.id}
                    onCreated={() => {
                      setAddPlotFarmId(null)
                      refreshPlots()
                    }}
                  />
                </Dialog>
              </div>

              {(plotsByFarm.get(farm.id) ?? []).length === 0 ? (
                <p className="text-sm text-pewter">No plots added yet -- crops attach directly to the farm.</p>
              ) : (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {(plotsByFarm.get(farm.id) ?? []).map((plot) => (
                    <div key={plot.id} className="relative rounded-card bg-card p-4 text-sm transition-colors hover:bg-ash-gray/60">
                      <Link to={`/plots/${plot.id}`} className="block">
                        <div className="flex items-center justify-between gap-2 pr-6">
                          <p className="font-medium text-charcoal">{plot.name}</p>
                          <span className="flex items-center gap-1 text-xs font-medium text-forest-ink">
                            <Sparkles className="size-3.5" /> Advisor
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-1.5 text-graphite">
                          {plot.latitude != null && plot.longitude != null ? (
                            <>
                              <MapPin className="size-3.5 text-status-safe" aria-hidden="true" />
                              {plot.latitude.toFixed(4)}, {plot.longitude.toFixed(4)}
                            </>
                          ) : (
                            <>
                              <MapPinOff className="size-3.5 text-status-warning" aria-hidden="true" />
                              <span className="italic">Location not configured</span>
                            </>
                          )}
                        </div>
                        <div className="mt-2">
                          <MLSourceBadge
                            source={plot.latitude != null && plot.longitude != null ? "estimated_downscaled" : "gp_level"}
                          />
                        </div>
                      </Link>
                      <button
                        type="button"
                        onClick={() => setDeletePlot(plot)}
                        className="absolute right-3 top-3 text-pewter hover:text-status-critical"
                        aria-label={`Delete ${plot.name}`}
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium text-graphite">🌱 Crops</h2>
                <Dialog
                  open={addCropFarmId === farm.id}
                  onOpenChange={(open) => setAddCropFarmId(open ? farm.id : null)}
                >
                  <DialogTrigger
                    render={
                      <Button variant="outline" size="sm">
                        <Plus className="size-4" /> Add Crop
                      </Button>
                    }
                  />
                  <AddCropDialog
                    farmId={farm.id}
                    onCreated={() => {
                      setAddCropFarmId(null)
                      refreshCrops()
                    }}
                  />
                </Dialog>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {(cropsByFarm.get(farm.id) ?? []).map((crop, i) => (
                  <CropCard
                    key={crop.id}
                    crop={crop}
                    toneIndex={i}
                    advisory={advisoryByCropId.get(crop.id)}
                    onEdit={() => setChangeCropOf(crop)}
                    onDelete={() => setDeleteCrop(crop)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {editFarm && (
        <Dialog open onOpenChange={(open) => !open && setEditFarm(null)}>
          <EditFarmDialog farm={editFarm} onSaved={() => { setEditFarm(null); refreshFarms() }} />
        </Dialog>
      )}
      {deleteFarm && (
        <Dialog open onOpenChange={(open) => !open && setDeleteFarm(null)}>
          <ConfirmDeleteDialog
            title={`Delete ${deleteFarm.name}?`}
            description="This removes the farm and everything linked to it. This cannot be undone."
            onConfirm={async () => {
              await api.deleteFarm(deleteFarm.id)
              setDeleteFarm(null)
              refreshFarms()
            }}
            onCancel={() => setDeleteFarm(null)}
          />
        </Dialog>
      )}
      {changeCropOf && (
        <Dialog open onOpenChange={(open) => !open && setChangeCropOf(null)}>
          <ChangeCropDialog crop={changeCropOf} onSaved={() => { setChangeCropOf(null); refreshCrops() }} />
        </Dialog>
      )}
      {deleteCrop && (
        <Dialog open onOpenChange={(open) => !open && setDeleteCrop(null)}>
          <ConfirmDeleteDialog
            title={`Delete ${deleteCrop.crop_name}?`}
            description="This removes this crop record. This cannot be undone."
            onConfirm={async () => {
              await api.deleteCrop(deleteCrop.id)
              setDeleteCrop(null)
              refreshCrops()
            }}
            onCancel={() => setDeleteCrop(null)}
          />
        </Dialog>
      )}
      {deletePlot && (
        <Dialog open onOpenChange={(open) => !open && setDeletePlot(null)}>
          <ConfirmDeleteDialog
            title={`Delete ${deletePlot.name}?`}
            description="This removes the plot. Crops linked only to this plot keep their farm-level record."
            onConfirm={async () => {
              await api.deletePlot(deletePlot.id)
              setDeletePlot(null)
              refreshPlots()
            }}
            onCancel={() => setDeletePlot(null)}
          />
        </Dialog>
      )}
    </div>
  )
}

function ConfirmDeleteDialog({
  title,
  description,
  onConfirm,
  onCancel,
}: {
  title: string
  description: string
  onConfirm: () => Promise<void>
  onCancel: () => void
}) {
  const [submitting, setSubmitting] = useState(false)
  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>
      <p className="text-sm text-graphite">{description}</p>
      <DialogFooter>
        <Button variant="outline" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button
          onClick={async () => {
            setSubmitting(true)
            try {
              await onConfirm()
            } finally {
              setSubmitting(false)
            }
          }}
          disabled={submitting}
          className="bg-status-critical hover:bg-status-critical/90"
        >
          {submitting ? "..." : "Delete"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function AddFarmDialog({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("")
  const [location, setLocation] = useState<LocationValue>(EMPTY_LOCATION)
  const [areaValue, setAreaValue] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async () => {
    setSubmitting(true)
    try {
      await api.createFarm({
        name,
        gram_panchayat: location.gramPanchayat,
        state: location.state || "Telangana",
        district: location.district,
        block: location.block,
        village: location.village || null,
        area_value: areaValue ? Number(areaValue) : null,
        area_unit: "acre",
        irrigation: null,
        soil_type: null,
      })
      onCreated()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Add Farm</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label>Farm name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Cotton Field" />
        </div>
        <p className="text-xs text-pewter">
          Select your farm's location -- no coordinates needed, FarmWise resolves weather and mapping
          automatically from the Panchayat you pick.
        </p>
        <LocationSelector value={location} onChange={setLocation} />
        <div className="space-y-1.5">
          <Label>Area (acres)</Label>
          <Input type="number" value={areaValue} onChange={(e) => setAreaValue(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={onSubmit} disabled={!name || !location.gramPanchayat || submitting}>
          {submitting ? "..." : "Save"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function EditFarmDialog({ farm, onSaved }: { farm: api.Farm; onSaved: () => void }) {
  const [name, setName] = useState(farm.name)
  const [areaValue, setAreaValue] = useState(farm.area_value != null ? String(farm.area_value) : "")
  const [irrigation, setIrrigation] = useState(farm.irrigation ?? "")
  const [soilType, setSoilType] = useState(farm.soil_type ?? "")
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async () => {
    setSubmitting(true)
    try {
      await api.updateFarm(farm.id, {
        name,
        area_value: areaValue ? Number(areaValue) : null,
        irrigation: irrigation || null,
        soil_type: soilType || null,
      })
      onSaved()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Edit Farm</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label>Farm name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <p className="text-xs text-pewter">
          Location ({[farm.village, farm.gram_panchayat, farm.block, farm.district].filter(Boolean).join(", ")}) can't
          be changed here -- delete and re-add the farm to move it to a different Panchayat.
        </p>
        <div className="space-y-1.5">
          <Label>Area (acres)</Label>
          <Input type="number" value={areaValue} onChange={(e) => setAreaValue(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>Irrigation type</Label>
          <Input value={irrigation} onChange={(e) => setIrrigation(e.target.value)} placeholder="Borewell, Canal, Rainfed..." />
        </div>
        <div className="space-y-1.5">
          <Label>Soil type</Label>
          <Input value={soilType} onChange={(e) => setSoilType(e.target.value)} placeholder="Black soil, Red soil..." />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={onSubmit} disabled={!name || submitting}>
          {submitting ? "..." : "Save"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function AddPlotDialog({ farmId, onCreated }: { farmId: string; onCreated: () => void }) {
  const [name, setName] = useState("")
  const [latitude, setLatitude] = useState("")
  const [longitude, setLongitude] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async () => {
    setSubmitting(true)
    try {
      await api.createPlot(farmId, {
        name,
        latitude: latitude ? Number(latitude) : null,
        longitude: longitude ? Number(longitude) : null,
        boundary_geojson: null,
        area_value: null,
        area_unit: "acre",
      })
      onCreated()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Add Plot</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label>Plot name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="North Field" />
        </div>
        <p className="text-xs text-pewter">
          Coordinates are optional. Without them, weather is shown at Gram Panchayat level; with them,
          rainfall is spatially estimated to this exact point.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label>Latitude</Label>
            <Input type="number" step="any" value={latitude} onChange={(e) => setLatitude(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Longitude</Label>
            <Input type="number" step="any" value={longitude} onChange={(e) => setLongitude(e.target.value)} />
          </div>
        </div>
      </div>
      <DialogFooter>
        <Button onClick={onSubmit} disabled={!name || submitting}>
          {submitting ? "..." : "Save"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function AddCropDialog({ farmId, onCreated }: { farmId: string; onCreated: () => void }) {
  const [value, setValue] = useState<CropSelectorValue>({ cropName: "", variety: "", stage: "" })
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async () => {
    setSubmitting(true)
    try {
      await api.createCrop({
        farm_id: farmId,
        crop_name: value.cropName,
        variety: value.variety || null,
        stage: value.stage,
        sowing_date: null,
        area_value: null,
        area_unit: "acre",
      })
      onCreated()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Add Crop</DialogTitle>
      </DialogHeader>
      <CropSelector value={value} onChange={setValue} />
      <DialogFooter>
        <Button onClick={onSubmit} disabled={!value.cropName || submitting}>
          {submitting ? "..." : "Save"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function ChangeCropDialog({ crop, onSaved }: { crop: Crop; onSaved: () => void }) {
  const [value, setValue] = useState<CropSelectorValue>({
    cropName: crop.crop_name,
    variety: crop.variety ?? "",
    stage: crop.stage,
  })
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async () => {
    setSubmitting(true)
    try {
      await api.updateCrop(crop.id, { crop_name: value.cropName, variety: value.variety || null, stage: value.stage })
      onSaved()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Change Crop</DialogTitle>
      </DialogHeader>
      <p className="text-xs text-pewter">
        Current: 🌾 {crop.crop_name} ({crop.stage}). Changing the crop updates the disease/weather/fertilizer
        guidance this plot sees -- it does not fabricate new history.
      </p>
      <CropSelector value={value} onChange={setValue} />
      <DialogFooter>
        <Button onClick={onSubmit} disabled={!value.cropName || submitting}>
          {submitting ? "..." : "Save"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}
