/**
 * Typed API client for the FastAPI backend (src/api.py). All business logic
 * (severity, risk aggregation) lives in lib/advisory.ts, not here or in
 * components -- this file only fetches and types data.
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000"

export class ApiError extends Error {
  status: number
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

const TOKEN_KEY = "access_token"

/** "Remember me" unchecked -> sessionStorage (cleared when the browser tab
 * closes); checked (default) -> localStorage (persists). */
function storeToken(token: string, remember: boolean): void {
  ;(remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token)
}

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY)
}

function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(TOKEN_KEY)
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...init?.headers,
    },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? JSON.stringify(body)
    } catch {
      // response wasn't JSON -- keep statusText
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ---- Types (mirror src/routers/*.py response shapes) ----

export interface User {
  id: string
  name: string
  email: string | null
  mobile: string | null
  language: string
  selected_state: string | null
  selected_district: string | null
  selected_block: string | null
  sms_notifications_enabled: boolean
  sms_alert_categories: SmsCategory[] | null
}

export type SmsCategory = "severe_weather" | "disease_risk" | "crop_stress" | "farm_actions"

export interface ForecastRow {
  date: string
  gram_panchayat: string
  rainfall_mm: number | null
  temp_max_c: number | null
  temp_min_c: number | null
  rh_max_pct: number | null
  wind_max_kmh: number | null
  confidence: "high" | "medium"
  advisory: string
}

export interface EstimatedHourPoint {
  hour: number
  temp_c: number
  estimated: true
}

export interface HourlyEstimated {
  gram_panchayat: string
  date: string
  points: EstimatedHourPoint[]
}

export type AlertSeverity = "critical" | "warning"

export interface Alert {
  gram_panchayat: string
  date: string
  icon: string
  severity: AlertSeverity
  title: string
  description: string
  action: string
}

export interface GpCentroid {
  gram_panchayat: string
  latitude: number
  longitude: number
}

export interface CropCatalogEntry {
  name: string
  varieties: string[]
  stages: string[]
}

export interface Farm {
  id: string
  owner_id: string
  name: string
  state: string
  district: string
  block: string
  gram_panchayat: string
  village: string | null
  area_value: number | null
  area_unit: string
  irrigation: string | null
  soil_type: string | null
  // Phase 0.5: plot-precision location. Null on farms created before this
  // field existed -- never inferred/invented, see docs/FOUNDATION.md.
  latitude: number | null
  longitude: number | null
  boundary_geojson: string | null
  location_name: string | null
}

export interface Crop {
  id: string
  farm_id: string
  plot_id: string | null
  crop_name: string
  variety: string | null
  sowing_date: string | null
  stage: string
  area_value: number | null
  area_unit: string
}

export interface Plot {
  id: string
  farm_id: string
  name: string
  latitude: number | null
  longitude: number | null
  boundary_geojson: string | null
  area_value: number | null
  area_unit: string
}

// ---- Auth ----

export function register(payload: {
  name: string
  password: string
  email?: string
  mobile?: string
}): Promise<User> {
  return request("/auth/register", { method: "POST", body: JSON.stringify(payload) })
}

export async function login(identifier: string, password: string, remember = true): Promise<User> {
  const { access_token } = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  })
  storeToken(access_token, remember)
  return getMe()
}

export function logout(): void {
  clearToken()
}

export function getMe(): Promise<User> {
  return request("/auth/me")
}

export function updateProfile(payload: {
  name?: string
  language?: string
  selected_state?: string
  selected_district?: string
  selected_block?: string
  sms_notifications_enabled?: boolean
  sms_alert_categories?: SmsCategory[]
}): Promise<User> {
  return request("/auth/me", { method: "PATCH", body: JSON.stringify(payload) })
}

export function forgotPassword(identifier: string): Promise<{ detail: string }> {
  return request("/auth/forgot-password", { method: "POST", body: JSON.stringify({ identifier }) })
}

export function resetPassword(token: string, new_password: string): Promise<{ detail: string }> {
  return request("/auth/reset-password", { method: "POST", body: JSON.stringify({ token, new_password }) })
}

// ---- Weather / forecast (existing read-only pipeline endpoints) ----

export function getGps(): Promise<GpCentroid[]> {
  return request("/gps")
}

export function getForecast(): Promise<ForecastRow[]> {
  return request("/forecast")
}

export function getForecastForGp(gpName: string): Promise<ForecastRow[]> {
  return request(`/forecast/${encodeURIComponent(gpName)}`)
}

export function getCurrentWeather(gpName: string): Promise<ForecastRow> {
  return request(`/weather/current/${encodeURIComponent(gpName)}`)
}

export function getHourlyEstimated(gpName: string, date?: string): Promise<HourlyEstimated> {
  const qs = date ? `?${new URLSearchParams({ date })}` : ""
  return request(`/weather/hourly-estimated/${encodeURIComponent(gpName)}${qs}`)
}

export function getAlertsForGp(gpName: string): Promise<Alert[]> {
  return request(`/alerts/${encodeURIComponent(gpName)}`)
}

export function getAllAlerts(): Promise<Alert[]> {
  return request("/alerts")
}

// ---- Locations ----

export function getStates(): Promise<string[]> {
  return request("/locations/states")
}

export function getDistricts(state: string): Promise<string[]> {
  return request(`/locations/districts?${new URLSearchParams({ state })}`)
}

export function getBlocks(state: string, district: string): Promise<string[]> {
  return request(`/locations/blocks?${new URLSearchParams({ state, district })}`)
}

export function getPanchayats(state: string, district: string, block: string): Promise<string[]> {
  return request(`/locations/panchayats?${new URLSearchParams({ state, district, block })}`)
}

export function getVillages(
  state: string,
  district: string,
  block: string,
  gramPanchayat: string
): Promise<string[]> {
  return request(
    `/locations/villages?${new URLSearchParams({ state, district, block, gram_panchayat: gramPanchayat })}`
  )
}

export function getCropCatalog(): Promise<CropCatalogEntry[]> {
  return request("/locations/crops")
}

// ---- Farms / Crops ----

export function listFarms(): Promise<Farm[]> {
  return request("/farms")
}

export function getFarm(id: string): Promise<Farm> {
  return request(`/farms/${id}`)
}

type FarmLocationFields = "latitude" | "longitude" | "boundary_geojson" | "location_name"

export function createFarm(
  payload: Omit<Farm, "id" | "owner_id" | FarmLocationFields> & Partial<Pick<Farm, FarmLocationFields>>
): Promise<Farm> {
  return request("/farms", { method: "POST", body: JSON.stringify(payload) })
}

export function updateFarm(id: string, payload: Partial<Farm>): Promise<Farm> {
  return request(`/farms/${id}`, { method: "PATCH", body: JSON.stringify(payload) })
}

export function deleteFarm(id: string): Promise<void> {
  return request(`/farms/${id}`, { method: "DELETE" })
}

export function listCrops(farmId?: string): Promise<Crop[]> {
  const qs = farmId ? `?${new URLSearchParams({ farm_id: farmId })}` : ""
  return request(`/crops${qs}`)
}

export function createCrop(payload: Omit<Crop, "id" | "plot_id"> & Partial<Pick<Crop, "plot_id">>): Promise<Crop> {
  return request("/crops", { method: "POST", body: JSON.stringify(payload) })
}

export function updateCrop(id: string, payload: Partial<Crop>): Promise<Crop> {
  return request(`/crops/${id}`, { method: "PATCH", body: JSON.stringify(payload) })
}

export function deleteCrop(id: string): Promise<void> {
  return request(`/crops/${id}`, { method: "DELETE" })
}

// ---- Plots (Phase 0.5) ----

export function listPlots(farmId: string): Promise<Plot[]> {
  return request(`/farms/${farmId}/plots`)
}

export function getPlot(id: string): Promise<Plot> {
  return request(`/plots/${id}`)
}

export function createPlot(
  farmId: string,
  payload: Omit<Plot, "id" | "farm_id">
): Promise<Plot> {
  return request(`/farms/${farmId}/plots`, { method: "POST", body: JSON.stringify(payload) })
}

export function updatePlot(id: string, payload: Partial<Plot>): Promise<Plot> {
  return request(`/plots/${id}`, { method: "PATCH", body: JSON.stringify(payload) })
}

export function deletePlot(id: string): Promise<void> {
  return request(`/plots/${id}`, { method: "DELETE" })
}

export type ValueSource = "gp_level" | "estimated_downscaled" | "pass_through"

export interface PlotWeatherField {
  value: number | null
  source: ValueSource
  method?: string | null
  provenance?: { gram_panchayat: string; distance_km: number; weight: number }[] | null
}

export interface PlotWeather {
  plot_id: string
  gram_panchayat: string
  date: string
  rainfall_mm: PlotWeatherField
  temp_max_c: PlotWeatherField
  temp_min_c: PlotWeatherField
  rh_max_pct: PlotWeatherField
  wind_max_kmh: PlotWeatherField
}

export type MlClassification = "REAL_ML_PREDICTION" | "RULE_BASED_LOGIC" | "RAW_DATA_API_VALUE" | "PASS_THROUGH_VALUE"

export interface PlotMlPrediction {
  variable: string
  classification: MlClassification
  model: string | null
  gp_level_value: number | null
  plot_estimate: { value: number; method: string; sources: unknown[] } | null
  note: string
}

export function getPlotWeather(plotId: string): Promise<PlotWeather> {
  return request(`/plots/${plotId}/weather`)
}

export function getPlotMlPredictions(plotId: string): Promise<{ plot_id: string; date: string; predictions: PlotMlPrediction[] }> {
  return request(`/plots/${plotId}/ml-predictions`)
}

export function getPlotRisk(plotId: string): Promise<{ plot_id: string; date: string; rainfall_source: ValueSource; alert: Alert | null }> {
  return request(`/plots/${plotId}/risk`)
}

export function getPlotHealth(plotId: string): Promise<{ plot_id: string; available: boolean; classification: string; reason: string }> {
  return request(`/plots/${plotId}/health`)
}

export function getPlotAdvisory(plotId: string): Promise<{
  plot_id: string
  date: string
  rainfall_source: ValueSource
  severity: string
  condition: string
  what: string
  why: string
  action: string
  crop_name: string | null
  stage: string | null
}> {
  return request(`/plots/${plotId}/advisory`)
}

// ---- AI Farm Advisor (Phase 1) ----

export type RecommendationStatus = "recommended" | "delay" | "avoid" | "monitor" | "normal"
export type RecommendationCategory =
  | "irrigation"
  | "fertilizer"
  | "disease_monitoring"
  | "field_inspection"
  | "weather_precautions"
  | "general_operations"

export interface Recommendation {
  category: RecommendationCategory
  status: RecommendationStatus
  what: string
  why: string
  when: string
  data_sources: string[]
}

export interface ActionPlanItem {
  priority: number
  category: RecommendationCategory
  status: RecommendationStatus
  label: string
}

export interface RiskCard {
  available: boolean
  level: "LOW" | "MEDIUM" | "HIGH" | null
  classification: MlClassification
  why: string
}

export interface CropConditionCard {
  available: false
  reason: string
  crop_name: string | null
  stage: string | null
}

export interface FarmAdvisorResponse {
  plot_id: string
  date: string
  crop: { crop_name: string; variety: string | null; stage: string } | null
  disease_risk: RiskCard
  weather_risk: RiskCard
  crop_condition: CropConditionCard
  recommendations: Recommendation[]
  action_plan: ActionPlanItem[]
  technical_details: {
    data_used: Record<string, { value: number | null; source: ValueSource }>
    ml_prediction_used: {
      variable: string
      model_name: string
      classification: MlClassification
      gp_level_value: number | null
    }
    spatial_estimation_used: { value: number; method: string; sources: unknown[] } | null
    rules_triggered: string[]
    timestamp: string
  }
}

export function getFarmAdvisor(plotId: string): Promise<FarmAdvisorResponse> {
  return request(`/plots/${plotId}/farm-advisor`)
}

// ---- Crop Health & Stress Intelligence (Phase 2) ----

export type SourceType = "ml_prediction" | "weather_data" | "soil_data" | "spatial_estimation" | "derived_assessment" | "unavailable"

export interface HealthStatus {
  available: boolean
  status: "GOOD" | "FAIR" | "POOR" | null
  label: string | null
  source_type: SourceType
  reason: string
}

export interface StressStatus {
  available: boolean
  status: "LOW" | "MEDIUM" | "HIGH" | null
  source_type: SourceType
  reason: string
}

export interface HealthFactor {
  key: string
  label: string
  value: string | null
  status: string
  available: boolean
  source_type: SourceType
}

export interface CropHealthResponse {
  plot_id: string
  date: string
  crop: { crop_name: string; stage: string } | null
  health: HealthStatus
  stress: StressStatus
  factors: HealthFactor[]
  explanation: { available: false; reason: string }
  health_trend: { available: false; reason: string }
  advisor_summary: { disease_risk_level: string | null; top_recommendation: string | null }
  technical_details: {
    model: string | null
    source: SourceType
    features_used: string[]
    timestamp: string
  }
}

export function getCropHealth(plotId: string): Promise<CropHealthResponse> {
  return request(`/plots/${plotId}/crop-health`)
}

// ---- Farm Intelligence Map (Phase 3) ----

export interface PlotIntelligence {
  plot_id: string
  plot_name: string
  farm_id: string
  farm_name: string
  latitude: number | null
  longitude: number | null
  location_configured: boolean
  area_value: number | null
  area_unit: string
  crop: { crop_name: string; variety: string | null; stage: string } | null
  date: string
  health: HealthStatus
  disease_risk: RiskCard
  weather_risk: RiskCard
  weather: {
    temp_max_c: { value: number | null; status: string; source: ValueSource }
    rh_max_pct: { value: number | null; status: string; source: ValueSource }
    rainfall_mm: { value: number | null; status: string; source: ValueSource }
  }
  top_recommendation: string | null
  active_alerts: PlotAlertSummary
  sources: {
    weather: string
    health: string
    disease_risk: string
    spatial_estimation_used: boolean
    resolution: string
  }
}

export function getPlotsIntelligence(): Promise<PlotIntelligence[]> {
  return request("/plots/intelligence")
}

// ---- Historical + Forecast Analytics (Phase 4) ----

export type InsightSource = "weather_history" | "forecast" | "ml_prediction" | "spatial_estimate" | "derived_rule"

export interface HistoricalWeather {
  available: boolean
  reason?: string
  range_days?: number
  start_date?: string
  end_date?: string
  temperature?: { date: string; max_c: number; min_c: number }[]
  rainfall?: { date: string; mm: number }[]
  humidity?: { date: string; max_pct: number }[]
  wind?: { date: string; max_kmh: number }[]
  source_type?: string
  note?: string
}

export interface RainfallAnalytics {
  available: boolean
  reason?: string
  total_mm?: number
  average_mm_per_day?: number
  rainy_days?: number
  highest_day?: { date: string; mm: number }
  comparison?: {
    available: boolean
    recent_average_mm_per_day: number
    reference_average_mm_per_day: number
    reference_period: string
  } | null
}

export interface ForecastDay {
  date: string
  temp_max_c: number | null
  temp_min_c: number | null
  rh_max_pct: number | null
  rainfall_mm: number | null
  wind_max_kmh: number | null
  condition: string
}

export interface ForecastRiskItem {
  level: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"
  source_type: SourceType | "derived_assessment"
  label: string
  [key: string]: unknown
}

export interface PlotAnalyticsResponse {
  plot_id: string
  date: string
  crop: { crop_name: string; stage: string } | null
  requested_range_days: number
  available_ranges: Record<string, boolean>
  historical: HistoricalWeather
  rainfall_analytics: RainfallAnalytics
  forecast: ForecastDay[]
  forecast_risk: {
    heavy_rain_risk: ForecastRiskItem
    heat_risk: ForecastRiskItem
    humidity_risk: ForecastRiskItem
    wind_risk: ForecastRiskItem
  } | null
  disease_history: { available: false; reason: string }
  health_history: { available: false; reason: string }
  insights: { text: string; source_type: InsightSource }[]
  advisor_summary: { disease_risk_level: string | null; weather_risk_level: string | null; top_recommendation: string | null }
  data_sources: Record<string, string>
  timestamp: string
}

export function getPlotAnalytics(plotId: string, rangeDays: 7 | 30 | 90 = 30): Promise<PlotAnalyticsResponse> {
  return request(`/plots/${plotId}/analytics?range_days=${rangeDays}`)
}

// ---- Smart Alerts & Early Warning System (Phase 5) ----

export type AlertSeverity4 = "critical" | "warning" | "attention" | "info"
export type AlertStatus = "new" | "read" | "resolved" | "expired"
export type AlertSourceType =
  | "weather_observation"
  | "weather_forecast"
  | "ml_prediction"
  | "spatial_estimation"
  | "derived_assessment"
  | "advisory_engine"

export interface FarmAlert {
  id: string
  farm_id: string
  farm_name: string
  plot_id: string | null
  plot_name: string | null
  crop_name: string | null
  alert_type: string
  severity: AlertSeverity4
  title: string
  condition: string
  reason: string
  recommended_action: string
  source: AlertSourceType
  status: AlertStatus
  valid_until: string | null
  created_at: string
  sms: {
    status: "SENT" | "DELIVERED" | "FAILED" | "NOT_SENT" | "DISABLED" | "NOT_APPLICABLE"
    simulated: boolean
  }
}

export interface PlotAlertSummary {
  counts: Record<AlertSeverity4, number>
  total: number
  top_severity: AlertSeverity4 | null
  top_emoji: string
}

export function getAlertCenterAlerts(): Promise<FarmAlert[]> {
  return request("/alert-center")
}

export function getFarmAlerts(farmId: string): Promise<FarmAlert[]> {
  return request(`/farms/${farmId}/alerts`)
}

export function getPlotAlerts(plotId: string): Promise<FarmAlert[]> {
  return request(`/plots/${plotId}/alerts`)
}

export function markAlertRead(alertId: string): Promise<FarmAlert> {
  return request(`/alerts/${alertId}/read`, { method: "PATCH" })
}

export function resolveAlert(alertId: string): Promise<FarmAlert> {
  return request(`/alerts/${alertId}/resolve`, { method: "PATCH" })
}

// ---- ML audit (Phase 0.5) ----

export interface MlAuditComponent {
  component: string
  display_name: string
  classification: MlClassification
  input_features: string[]
  output: string
  training_data: string
  spatial_resolution: string
  temporal_resolution: string
  model_type: string
  how_loaded: string
  how_predictions_generated: string
}

export function getMlModels(): Promise<MlAuditComponent[]> {
  return request("/ml/models")
}

export interface CropAdvisory {
  crop_id: string
  date: string
  severity: "critical" | "warning" | "safe"
  condition: "heavy_rain" | "heat_stress" | "fungal_risk" | "normal"
  what: string
  why: string
  action: string
  crop_name: string
  stage: string
}

export function getCropAdvisoryForFarm(farmId: string): Promise<CropAdvisory[]> {
  return request(`/farms/${farmId}/crop-advisory`)
}

// ---- Notifications ----

export interface AppNotification {
  id: string
  title: string
  body: string
  severity: "critical" | "warning" | "safe" | "info"
  read: boolean
  created_at: string
}

export function getNotifications(): Promise<AppNotification[]> {
  return request("/notifications")
}

export function markNotificationRead(id: string): Promise<void> {
  return request(`/notifications/${id}/read`, { method: "POST" })
}

export function markAllNotificationsRead(): Promise<void> {
  return request("/notifications/read-all", { method: "POST" })
}

// ---- Farm management: disease reports, inspections, activity log ----

export interface DiseaseReport {
  id: string
  farm_id: string
  plot_id: string | null
  crop_id: string | null
  observed_problem: string
  symptoms: string | null
  observed_date: string | null
  notes: string | null
  ai_guidance: string | null
  ai_source: string | null
  created_at: string
}

export function listDiseaseReports(farmId?: string): Promise<DiseaseReport[]> {
  const qs = farmId ? `?${new URLSearchParams({ farm_id: farmId })}` : ""
  return request(`/disease-reports${qs}`)
}

export function createDiseaseReport(payload: {
  farm_id: string
  plot_id?: string | null
  crop_id?: string | null
  observed_problem: string
  symptoms?: string | null
  observed_date?: string | null
  notes?: string | null
}): Promise<DiseaseReport> {
  return request("/disease-reports", { method: "POST", body: JSON.stringify(payload) })
}

export function analyzeDiseaseReport(id: string): Promise<DiseaseReport> {
  return request(`/disease-reports/${id}/analyze`, { method: "POST" })
}

export interface InspectionRecord {
  id: string
  farm_id: string
  plot_id: string | null
  crop_id: string | null
  inspection_date: string
  observed_symptoms: string | null
  pest_or_disease: string | null
  crop_condition: string | null
  notes: string | null
  created_at: string
}

export function listInspections(farmId?: string): Promise<InspectionRecord[]> {
  const qs = farmId ? `?${new URLSearchParams({ farm_id: farmId })}` : ""
  return request(`/inspections${qs}`)
}

export function createInspection(payload: {
  farm_id: string
  plot_id?: string | null
  crop_id?: string | null
  inspection_date: string
  observed_symptoms?: string | null
  pest_or_disease?: string | null
  crop_condition?: string | null
  notes?: string | null
}): Promise<InspectionRecord> {
  return request("/inspections", { method: "POST", body: JSON.stringify(payload) })
}

export type FarmActivityType = "irrigation" | "fertilizer" | "inspection" | "sowing" | "spraying" | "harvesting" | "weeding" | "other"

export interface FarmActivity {
  id: string
  farm_id: string
  plot_id: string | null
  crop_id: string | null
  activity_type: FarmActivityType
  activity_date: string
  notes: string | null
  created_at: string
}

export function listFarmActivities(farmId?: string): Promise<FarmActivity[]> {
  const qs = farmId ? `?${new URLSearchParams({ farm_id: farmId })}` : ""
  return request(`/farm-activities${qs}`)
}

export function createFarmActivity(payload: {
  farm_id: string
  plot_id?: string | null
  crop_id?: string | null
  activity_type: FarmActivityType
  activity_date: string
  notes?: string | null
}): Promise<FarmActivity> {
  return request("/farm-activities", { method: "POST", body: JSON.stringify(payload) })
}
