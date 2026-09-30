import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Plus } from "lucide-react"
import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"

import { EmptyState } from "@/components/EmptyState"
import { ErrorState } from "@/components/ErrorState"
import { LoadingState } from "@/components/LoadingState"
import { RecommendationCard } from "@/components/RecommendationCard"
import { RiskIndicator } from "@/components/RiskIndicator"
import { RiskLevelCard } from "@/components/RiskLevelCard"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { WeatherAlert } from "@/components/WeatherAlert"
import { fieldInspectionDecision } from "@/lib/advisory"
import * as api from "@/lib/api"
import { useSelectedGp } from "@/lib/useSelectedGp"
import { useSelectedPlot } from "@/lib/useSelectedPlot"

type RiskLevel = "LOW" | "MEDIUM" | "HIGH"
const RISK_ORDER: Record<RiskLevel, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 }

function worstLevel(levels: (RiskLevel | null | undefined)[]): RiskLevel | null {
  const present = levels.filter((l): l is RiskLevel => !!l)
  if (present.length === 0) return null
  return present.reduce((worst, l) => (RISK_ORDER[l] > RISK_ORDER[worst] ? l : worst))
}

const ACTIVITY_LABELS: Record<api.FarmActivityType, string> = {
  irrigation: "💧 Irrigation completed",
  fertilizer: "🧪 Fertilizer applied",
  inspection: "🔍 Inspection completed",
  sowing: "🌱 Sowing",
  spraying: "🌾 Spraying",
  harvesting: "🌾 Harvesting",
  weeding: "🚜 Weeding",
  other: "📝 Other",
}

export function FarmOverview() {
  const { farmId = "" } = useParams<{ farmId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { selectPlot } = useSelectedPlot()
  const { selectGp } = useSelectedGp()

  const farmQuery = useQuery({ queryKey: ["farm", farmId], queryFn: () => api.getFarm(farmId), enabled: !!farmId })
  const plotsQuery = useQuery({ queryKey: ["plots", farmId], queryFn: () => api.listPlots(farmId), enabled: !!farmId })
  const cropsQuery = useQuery({ queryKey: ["crops", farmId], queryFn: () => api.listCrops(farmId), enabled: !!farmId })
  const advisoryQuery = useQuery({
    queryKey: ["crop-advisory", farmId],
    queryFn: () => api.getCropAdvisoryForFarm(farmId),
    enabled: !!farmId,
  })
  const alertsQuery = useQuery({ queryKey: ["farm-alerts", farmId], queryFn: () => api.getFarmAlerts(farmId), enabled: !!farmId })
  const diseaseReportsQuery = useQuery({
    queryKey: ["disease-reports", farmId],
    queryFn: () => api.listDiseaseReports(farmId),
    enabled: !!farmId,
  })
  const inspectionsQuery = useQuery({
    queryKey: ["inspections", farmId],
    queryFn: () => api.listInspections(farmId),
    enabled: !!farmId,
  })
  const activitiesQuery = useQuery({
    queryKey: ["farm-activities", farmId],
    queryFn: () => api.listFarmActivities(farmId),
    enabled: !!farmId,
  })

  const plots = plotsQuery.data ?? []
  const plotAdvisorQueries = useQueries({
    queries: plots.map((p) => ({ queryKey: ["farm-advisor", p.id], queryFn: () => api.getFarmAdvisor(p.id) })),
  })
  const weatherQuery = useQuery({
    queryKey: ["weather-current", farmQuery.data?.gram_panchayat],
    queryFn: () => api.getCurrentWeather(farmQuery.data!.gram_panchayat),
    enabled: !!farmQuery.data,
  })

  const [reportDiseaseOpen, setReportDiseaseOpen] = useState(false)
  const [recordInspectionOpen, setRecordInspectionOpen] = useState(false)
  const [logActivityOpen, setLogActivityOpen] = useState(false)

  if (farmQuery.isLoading || plotsQuery.isLoading || cropsQuery.isLoading) return <LoadingState label="Loading farm..." />
  if (farmQuery.isError || !farmQuery.data) return <ErrorState message="Farm not found." />

  const farm = farmQuery.data
  const crops = cropsQuery.data ?? []
  const advisories = advisoryQuery.data ?? []
  const activeAlerts = (alertsQuery.data ?? []).filter((a) => a.status !== "resolved" && a.status !== "expired")
  const plotAdvisors = plotAdvisorQueries.map((q) => q.data).filter((d): d is api.FarmAdvisorResponse => !!d)
  const hasPlotData = plots.length > 0 && plotAdvisors.length > 0

  const worstCropSeverity = advisories.reduce<"critical" | "warning" | "safe">(
    (worst, a) => (a.severity === "critical" ? "critical" : a.severity === "warning" && worst !== "critical" ? "warning" : worst),
    "safe"
  )
  const diseaseLevel = worstLevel(plotAdvisors.map((a) => a.disease_risk.level))
  const weatherRiskLevel = worstLevel(plotAdvisors.map((a) => a.weather_risk.level))
  const irrigationRec = plotAdvisors
    .flatMap((a) => a.recommendations)
    .find((r) => r.category === "irrigation" && r.status !== "normal")
  const fertilizerRec = plotAdvisors.flatMap((a) => a.recommendations).find((r) => r.category === "fertilizer" && r.status !== "normal")

  // Farm Action Plan: merge each plot's action_plan, worst-priority first.
  const actionPlan = plotAdvisors
    .flatMap((a) => a.action_plan)
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 6)

  const openAdvisoryForFarm = () => {
    const firstPlot = plots[0]
    if (firstPlot) selectPlot(firstPlot.id)
    navigate("/advisory")
  }
  const openForecastForFarm = () => {
    selectGp(farm.gram_panchayat)
    navigate("/forecast")
  }

  const refresh = (key: string) => queryClient.invalidateQueries({ queryKey: [key, farmId] })

  return (
    <div className="space-y-6">
      <Link to="/farm" className="inline-flex items-center gap-1.5 text-sm text-forest-ink hover:underline">
        <ArrowLeft className="size-4" /> Back to My Farms
      </Link>

      {/* 7. Farm overview header */}
      <div>
        <h1 className="font-serif text-2xl font-medium text-charcoal">🌾 {farm.name}</h1>
        <p className="mt-1 text-sm text-graphite">
          📍 {[farm.state, farm.district, farm.block, farm.gram_panchayat].filter(Boolean).join(" → ")}
        </p>
        <p className="mt-1 text-sm text-graphite">
          {farm.area_value != null && `📐 ${farm.area_value} ${farm.area_unit} · `}
          🌱 {crops.length} crop{crops.length !== 1 ? "s" : ""} · 📐 {plots.length} plot{plots.length !== 1 ? "s" : ""}
        </p>
      </div>

      {/* 8. Today at your farm */}
      {weatherQuery.data && (
        <div className="rounded-card bg-card p-6">
          <h2 className="mb-4 font-serif text-lg font-medium text-charcoal">📅 Today at Your Farm</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-xs text-pewter">🌡 Temperature</p>
              <p className="text-sm font-medium text-charcoal">{weatherQuery.data.temp_max_c ?? "Data unavailable"}°C</p>
            </div>
            <div>
              <p className="text-xs text-pewter">💧 Humidity</p>
              <p className="text-sm font-medium text-charcoal">{weatherQuery.data.rh_max_pct ?? "Data unavailable"}%</p>
            </div>
            <div>
              <p className="text-xs text-pewter">🌧 Rainfall</p>
              <p className="text-sm font-medium text-charcoal">{weatherQuery.data.rainfall_mm ?? "Data unavailable"}mm</p>
            </div>
            <div>
              <p className="text-xs text-pewter">💨 Wind</p>
              <p className="text-sm font-medium text-charcoal">{weatherQuery.data.wind_max_kmh ?? "Data unavailable"}km/h</p>
            </div>
          </div>
        </div>
      )}

      {/* Current farm condition */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">Current Farm Condition</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <RiskLevelCard
            title="🌱 Crop Condition"
            level={advisories.length === 0 ? null : worstCropSeverity === "safe" ? "LOW" : worstCropSeverity === "warning" ? "MEDIUM" : "HIGH"}
            why={advisories.length === 0 ? "" : "From active crop advisories."}
            unavailableReason="No crops with advisory data yet."
          />
          <RiskLevelCard
            title="🦠 Disease Risk"
            level={diseaseLevel}
            why="From this farm's plot-level advisor."
            unavailableReason={hasPlotData ? "Not available." : "Add a plot for plot-level disease risk."}
            classification={hasPlotData ? "RULE_BASED_LOGIC" : undefined}
          />
          <RiskLevelCard
            title="🌦 Weather Risk"
            level={weatherRiskLevel}
            why="From this farm's plot-level advisor."
            unavailableReason={hasPlotData ? "Not available." : "Add a plot for plot-level weather risk."}
            classification={hasPlotData ? "RULE_BASED_LOGIC" : undefined}
          />
          <RiskLevelCard
            title="💧 Irrigation"
            level={irrigationRec ? (irrigationRec.status === "recommended" ? "MEDIUM" : "LOW") : null}
            why={irrigationRec?.what ?? ""}
            unavailableReason={hasPlotData ? "No irrigation concern right now." : "Add a plot for irrigation guidance."}
          />
          <RiskLevelCard
            title="🚨 Warnings"
            level={activeAlerts.length === 0 ? null : activeAlerts.length >= 3 ? "HIGH" : "MEDIUM"}
            why={`${activeAlerts.length} active warning${activeAlerts.length !== 1 ? "s" : ""}.`}
            unavailableReason="No active warnings."
          />
        </div>
      </div>

      {/* 9. Farm warnings */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🚨 Farm Warnings</h2>
        {activeAlerts.length === 0 ? (
          <div className="rounded-card bg-status-safe-bg p-4 text-sm font-medium text-status-safe">✓ No active farm warnings.</div>
        ) : (
          <div className="space-y-3">
            {activeAlerts.slice(0, 5).map((a) => (
              <WeatherAlert
                key={a.id}
                severity={a.severity === "attention" ? "warning" : a.severity === "info" ? "safe" : a.severity}
                title={a.title}
                description={`${a.reason}${a.plot_name ? ` — ${a.plot_name}` : ""}${a.crop_name ? ` (${a.crop_name})` : ""}`}
                action={a.recommended_action}
                dateLabel={new Date(a.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              />
            ))}
            <Button variant="outline" size="sm" onClick={openAdvisoryForFarm}>
              View Details in Advisory →
            </Button>
          </div>
        )}
      </div>

      {/* 10. Plots */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">📐 Plots</h2>
        {plots.length === 0 ? (
          <EmptyState message="No plots added yet. Add one from My Farms to unlock plot-level disease/weather/irrigation guidance." />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {plots.map((plot, i) => {
              const advisor = plotAdvisorQueries[i]?.data
              const plotCrop = crops.find((c) => c.plot_id === plot.id)
              return (
                <Link key={plot.id} to={`/plots/${plot.id}`} className="block rounded-card bg-card p-4 text-sm hover:bg-ash-gray/60">
                  <p className="font-medium text-charcoal">{plot.name}</p>
                  {plotCrop && (
                    <p className="text-graphite">
                      🌾 {plotCrop.crop_name} · 🌱 {plotCrop.stage}
                    </p>
                  )}
                  {advisor && (
                    <div className="mt-2 flex items-center gap-2">
                      {advisor.disease_risk.available && advisor.disease_risk.level && (
                        <span className="text-xs text-graphite">🦠 {advisor.disease_risk.level}</span>
                      )}
                      {advisor.weather_risk.available && advisor.weather_risk.level && (
                        <span className="text-xs text-graphite">🌦 {advisor.weather_risk.level}</span>
                      )}
                    </div>
                  )}
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* 15. Disease monitoring */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🦠 Disease Monitoring</h2>
        {hasPlotData ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {plots.map((plot, i) => {
              const advisor = plotAdvisorQueries[i]?.data
              if (!advisor) return null
              return (
                <RiskLevelCard
                  key={plot.id}
                  title={`🦠 ${plot.name}`}
                  level={advisor.disease_risk.level}
                  why={advisor.disease_risk.why}
                  classification={advisor.disease_risk.classification}
                />
              )
            })}
          </div>
        ) : (
          <EmptyState message="Add a plot to a crop to see plot-level disease risk here." />
        )}
      </div>

      {/* 16-17. Farmer-reported disease + Gemini assistance */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-serif text-lg font-medium text-charcoal">🦠 Report a Disease / Crop Problem</h2>
          <Dialog open={reportDiseaseOpen} onOpenChange={setReportDiseaseOpen}>
            <DialogTrigger render={<Button size="sm"><Plus className="size-4" /> Report</Button>} />
            <ReportDiseaseDialog
              farmId={farmId}
              plots={plots}
              crops={crops}
              onCreated={() => {
                setReportDiseaseOpen(false)
                refresh("disease-reports")
              }}
            />
          </Dialog>
        </div>
        {(diseaseReportsQuery.data ?? []).length === 0 ? (
          <EmptyState message="No disease reports yet." />
        ) : (
          <div className="space-y-3">
            {(diseaseReportsQuery.data ?? []).map((report) => (
              <DiseaseReportCard key={report.id} report={report} />
            ))}
          </div>
        )}
      </div>

      {/* 18. Fertilizer & nutrient management */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">🧪 Fertilizer &amp; Nutrient Management</h2>
        {fertilizerRec ? (
          <RecommendationCard recommendation={fertilizerRec} />
        ) : (
          <EmptyState message={hasPlotData ? "No fertilizer concern right now." : "Specific nutrient recommendation unavailable without soil information."} />
        )}
      </div>

      {/* 20. Irrigation */}
      <div>
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">💧 Irrigation</h2>
        {irrigationRec ? (
          <RecommendationCard recommendation={irrigationRec} />
        ) : (
          <EmptyState message={hasPlotData ? "No irrigation concern right now -- follow your regular schedule." : "Insufficient data -- add a plot for irrigation guidance."} />
        )}
      </div>

      {/* 21-22. Farm inspections */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-serif text-lg font-medium text-charcoal">🔍 Farm Inspections</h2>
          <Dialog open={recordInspectionOpen} onOpenChange={setRecordInspectionOpen}>
            <DialogTrigger render={<Button size="sm"><Plus className="size-4" /> Record Inspection</Button>} />
            <RecordInspectionDialog
              farmId={farmId}
              plots={plots}
              crops={crops}
              onCreated={() => {
                setRecordInspectionOpen(false)
                refresh("inspections")
              }}
            />
          </Dialog>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {plots.map((plot, i) => {
            const advisor = plotAdvisorQueries[i]?.data
            if (!advisor) return null
            const decision = fieldInspectionDecision(advisor)
            if (!decision) return null
            return (
              <div key={plot.id} className="rounded-card bg-card p-5">
                <p className="text-sm font-medium text-graphite">{plot.name}</p>
                <p className="mt-1 text-lg font-medium text-forest-ink">{decision.decision}</p>
                <p className="mt-1 text-xs text-graphite">{decision.why}</p>
                <p className="mt-1 text-xs text-pewter">Priority: {decision.priority} · {decision.when}</p>
              </div>
            )
          })}
        </div>
        {(inspectionsQuery.data ?? []).length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-sm font-medium text-graphite">Inspection history</p>
            {(inspectionsQuery.data ?? []).slice(0, 5).map((rec) => (
              <div key={rec.id} className="rounded-card bg-card p-3 text-xs text-graphite">
                {rec.inspection_date} · {rec.crop_condition ?? "Condition not noted"}
                {rec.pest_or_disease && ` · ${rec.pest_or_disease}`}
                {rec.notes && ` · ${rec.notes}`}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 23. Farm action plan */}
      <div className="rounded-card bg-card p-6">
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">📋 Farm Action Plan</h2>
        {actionPlan.length === 0 ? (
          <p className="text-sm text-status-safe">✓ No urgent actions today.</p>
        ) : (
          <ol className="space-y-1.5 text-sm text-charcoal">
            {actionPlan.map((item, i) => (
              <li key={`${item.category}-${i}`}>
                {i + 1}. {item.label}
              </li>
            ))}
          </ol>
        )}
      </div>

      {/* 24. Farm activity */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-serif text-lg font-medium text-charcoal">📝 Farm Activity</h2>
          <Dialog open={logActivityOpen} onOpenChange={setLogActivityOpen}>
            <DialogTrigger render={<Button size="sm"><Plus className="size-4" /> Log Activity</Button>} />
            <LogActivityDialog
              farmId={farmId}
              plots={plots}
              crops={crops}
              onCreated={() => {
                setLogActivityOpen(false)
                refresh("farm-activities")
              }}
            />
          </Dialog>
        </div>
        {(activitiesQuery.data ?? []).length === 0 ? (
          <EmptyState message="No activity logged yet." />
        ) : (
          <div className="space-y-2">
            {(activitiesQuery.data ?? []).slice(0, 8).map((activity) => (
              <div key={activity.id} className="rounded-card bg-card p-3 text-sm text-graphite">
                {ACTIVITY_LABELS[activity.activity_type]} · {activity.activity_date}
                {activity.notes && ` · ${activity.notes}`}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 25. Farm health summary */}
      <div className="rounded-card bg-card p-6">
        <h2 className="mb-3 font-serif text-lg font-medium text-charcoal">📊 Farm Health Summary</h2>
        <div className="flex flex-wrap gap-4 text-sm">
          <span>🌱 Crop Health: <RiskIndicator severity={worstCropSeverity} /></span>
          <span>🦠 Disease: {diseaseLevel ?? "Unknown"}</span>
          <span>🌦 Weather: {weatherRiskLevel ?? "Unknown"}</span>
          <span>🧪 Nutrients: {fertilizerRec ? "Attention" : "Normal"}</span>
          <span>🚨 Alerts: {activeAlerts.length}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={openForecastForFarm}>
          View Forecast
        </Button>
        <Button onClick={openAdvisoryForFarm}>Open Detailed Advisory →</Button>
      </div>
    </div>
  )
}

function ReportDiseaseDialog({
  farmId,
  plots,
  crops,
  onCreated,
}: {
  farmId: string
  plots: api.Plot[]
  crops: api.Crop[]
  onCreated: () => void
}) {
  const [plotId, setPlotId] = useState("")
  const [cropId, setCropId] = useState("")
  const [observedProblem, setObservedProblem] = useState("")
  const [symptoms, setSymptoms] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async () => {
    setSubmitting(true)
    try {
      await api.createDiseaseReport({
        farm_id: farmId,
        plot_id: plotId || null,
        crop_id: cropId || null,
        observed_problem: observedProblem,
        symptoms: symptoms || null,
        observed_date: new Date().toISOString().slice(0, 10),
      })
      onCreated()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Report a Disease / Crop Problem</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        {plots.length > 0 && (
          <div className="space-y-1.5">
            <Label>Plot (optional)</Label>
            <Select value={plotId} onValueChange={(v) => setPlotId(v ?? "")}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select plot" /></SelectTrigger>
              <SelectContent>{plots.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        {crops.length > 0 && (
          <div className="space-y-1.5">
            <Label>Crop (optional)</Label>
            <Select value={cropId} onValueChange={(v) => setCropId(v ?? "")}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select crop" /></SelectTrigger>
              <SelectContent>{crops.map((c) => <SelectItem key={c.id} value={c.id}>{c.crop_name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        <div className="space-y-1.5">
          <Label>What have you observed?</Label>
          <Input value={observedProblem} onChange={(e) => setObservedProblem(e.target.value)} placeholder="e.g. I think my rice has blast disease" />
        </div>
        <div className="space-y-1.5">
          <Label>Symptoms</Label>
          <Input value={symptoms} onChange={(e) => setSymptoms(e.target.value)} placeholder="e.g. brown lesions on leaves" />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={onSubmit} disabled={!observedProblem || submitting}>
          {submitting ? "..." : "Submit report"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function DiseaseReportCard({ report }: { report: api.DiseaseReport }) {
  const [analyzing, setAnalyzing] = useState(false)
  const [guidance, setGuidance] = useState(report.ai_guidance)
  const [error, setError] = useState<string | null>(null)

  const onAnalyze = async () => {
    setAnalyzing(true)
    setError(null)
    try {
      const updated = await api.analyzeDiseaseReport(report.id)
      setGuidance(updated.ai_guidance)
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "AI guidance is not available right now.")
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="rounded-card bg-card p-5">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium text-charcoal">{report.observed_problem}</p>
        <span className="rounded-full bg-ash-gray px-3 py-1 text-xs font-medium text-graphite">Farmer-reported</span>
      </div>
      {report.symptoms && <p className="mt-1 text-sm text-graphite">Symptoms: {report.symptoms}</p>}
      <p className="mt-1 text-xs text-pewter">{report.observed_date ?? report.created_at.slice(0, 10)}</p>

      {guidance ? (
        <div className="mt-3 rounded-xl bg-sage-card p-3 text-sm text-charcoal">
          <p className="mb-1 font-medium">🤖 AI Guidance ({report.ai_source})</p>
          <p className="whitespace-pre-line">{guidance}</p>
        </div>
      ) : (
        <div className="mt-3">
          <Button size="sm" variant="outline" onClick={onAnalyze} disabled={analyzing}>
            {analyzing ? "..." : "Analyze / Get Recommendation"}
          </Button>
          {error && <p className="mt-2 text-xs italic text-pewter">{error}</p>}
        </div>
      )}
    </div>
  )
}

function RecordInspectionDialog({
  farmId,
  plots,
  crops,
  onCreated,
}: {
  farmId: string
  plots: api.Plot[]
  crops: api.Crop[]
  onCreated: () => void
}) {
  const [plotId, setPlotId] = useState("")
  const [cropId, setCropId] = useState("")
  const [cropCondition, setCropCondition] = useState("")
  const [observedSymptoms, setObservedSymptoms] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async () => {
    setSubmitting(true)
    try {
      await api.createInspection({
        farm_id: farmId,
        plot_id: plotId || null,
        crop_id: cropId || null,
        inspection_date: new Date().toISOString().slice(0, 10),
        crop_condition: cropCondition || null,
        observed_symptoms: observedSymptoms || null,
      })
      onCreated()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Record Inspection</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        {plots.length > 0 && (
          <div className="space-y-1.5">
            <Label>Plot</Label>
            <Select value={plotId} onValueChange={(v) => setPlotId(v ?? "")}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select plot" /></SelectTrigger>
              <SelectContent>{plots.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        {crops.length > 0 && (
          <div className="space-y-1.5">
            <Label>Crop</Label>
            <Select value={cropId} onValueChange={(v) => setCropId(v ?? "")}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select crop" /></SelectTrigger>
              <SelectContent>{crops.map((c) => <SelectItem key={c.id} value={c.id}>{c.crop_name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        <div className="space-y-1.5">
          <Label>Crop condition observed</Label>
          <Input value={cropCondition} onChange={(e) => setCropCondition(e.target.value)} placeholder="e.g. Healthy" />
        </div>
        <div className="space-y-1.5">
          <Label>Observed symptoms (if any)</Label>
          <Input value={observedSymptoms} onChange={(e) => setObservedSymptoms(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={onSubmit} disabled={submitting}>
          {submitting ? "..." : "Save inspection"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function LogActivityDialog({
  farmId,
  plots,
  crops,
  onCreated,
}: {
  farmId: string
  plots: api.Plot[]
  crops: api.Crop[]
  onCreated: () => void
}) {
  const [activityType, setActivityType] = useState<api.FarmActivityType>("irrigation")
  const [plotId, setPlotId] = useState("")
  const [cropId, setCropId] = useState("")
  const [notes, setNotes] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async () => {
    setSubmitting(true)
    try {
      await api.createFarmActivity({
        farm_id: farmId,
        plot_id: plotId || null,
        crop_id: cropId || null,
        activity_type: activityType,
        activity_date: new Date().toISOString().slice(0, 10),
        notes: notes || null,
      })
      onCreated()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Log Farm Activity</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label>Activity</Label>
          <Select value={activityType} onValueChange={(v) => v && setActivityType(v as api.FarmActivityType)}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              {(Object.keys(ACTIVITY_LABELS) as api.FarmActivityType[]).map((key) => (
                <SelectItem key={key} value={key}>{ACTIVITY_LABELS[key]}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {plots.length > 0 && (
          <div className="space-y-1.5">
            <Label>Plot (optional)</Label>
            <Select value={plotId} onValueChange={(v) => setPlotId(v ?? "")}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select plot" /></SelectTrigger>
              <SelectContent>{plots.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        {crops.length > 0 && (
          <div className="space-y-1.5">
            <Label>Crop (optional)</Label>
            <Select value={cropId} onValueChange={(v) => setCropId(v ?? "")}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select crop" /></SelectTrigger>
              <SelectContent>{crops.map((c) => <SelectItem key={c.id} value={c.id}>{c.crop_name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        <div className="space-y-1.5">
          <Label>Notes</Label>
          <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={onSubmit} disabled={submitting}>
          {submitting ? "..." : "Save"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}
