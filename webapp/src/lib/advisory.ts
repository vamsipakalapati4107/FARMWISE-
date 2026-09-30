/**
 * Severity classification for a forecast row. Mirrors the thresholds in
 * src/advisory_rules.py exactly (HEAVY_RAIN_THRESHOLD_MM=20,
 * HEAT_STRESS_THRESHOLD_C=38, HUMID_RH_THRESHOLD_PCT=85,
 * HUMID_RAIN_THRESHOLD_MM=5) rather than string-matching the advisory text,
 * so severity classification works independent of language/i18n.
 *
 * This is an interim client-side mirror of the backend rule; Phase 11 adds a
 * structured /alerts endpoint that will replace it as the source of truth.
 */
import type { FarmAdvisorResponse, ForecastRow } from "./api"

export type Severity = "critical" | "warning" | "safe"

export interface Classification {
  severity: Severity
  label: string
}

const HEAVY_RAIN_THRESHOLD_MM = 20
const HEAT_STRESS_THRESHOLD_C = 38
const HUMID_RH_THRESHOLD_PCT = 85
const HUMID_RAIN_THRESHOLD_MM = 5

export function classifyForecastRow(row: Pick<ForecastRow, "rainfall_mm" | "temp_max_c" | "rh_max_pct">): Classification {
  const { rainfall_mm, temp_max_c, rh_max_pct } = row

  if (rainfall_mm != null && rainfall_mm > HEAVY_RAIN_THRESHOLD_MM) {
    return { severity: "critical", label: "Heavy rain" }
  }
  if (temp_max_c != null && temp_max_c > HEAT_STRESS_THRESHOLD_C) {
    return { severity: "critical", label: "Heat stress" }
  }
  if (
    rh_max_pct != null &&
    rainfall_mm != null &&
    rh_max_pct > HUMID_RH_THRESHOLD_PCT &&
    rainfall_mm > HUMID_RAIN_THRESHOLD_MM
  ) {
    return { severity: "warning", label: "Fungal disease risk" }
  }
  return { severity: "safe", label: "Normal operations" }
}

export const SEVERITY_STYLES: Record<Severity, { text: string; bg: string; border: string }> = {
  critical: { text: "text-status-critical", bg: "bg-status-critical-bg", border: "border-status-critical" },
  warning: { text: "text-status-warning", bg: "bg-status-warning-bg", border: "border-status-warning" },
  safe: { text: "text-status-safe", bg: "bg-status-safe-bg", border: "border-status-safe" },
}

/** Aggregate severity across a set of rows (e.g. a GP's 5-day forecast) -- worst-case wins. */
export function aggregateSeverity(rows: Classification[]): Severity {
  if (rows.some((r) => r.severity === "critical")) return "critical"
  if (rows.some((r) => r.severity === "warning")) return "warning"
  return "safe"
}

export interface AdvisoryDetail {
  severity: Severity
  what: string
  why: string
  action: string
}

/**
 * Structures the backend's single advisory sentence (src/advisory_rules.py)
 * into the What/Why/Action shape farmers need (spec section 7). The four
 * branches mirror generate_advisory()'s own branches exactly -- this is
 * presentation copy for an already-real classification, not invented data.
 */
export function buildAdvisoryDetail(row: Pick<ForecastRow, "rainfall_mm" | "temp_max_c" | "rh_max_pct">): AdvisoryDetail {
  const { severity, label } = classifyForecastRow(row)

  if (label === "Heavy rain") {
    return {
      severity,
      what: "Heavy rain expected (over 20mm).",
      why: "Waterlogged fields and washed-off spray reduce yield and waste input cost.",
      action: "Delay spraying and harvest; check field drainage before the rain arrives.",
    }
  }
  if (label === "Heat stress") {
    return {
      severity,
      what: "High daytime temperature expected (over 38°C).",
      why: "Midday heat stresses crops and increases water loss.",
      action: "Irrigate early morning or evening; avoid fieldwork during peak heat.",
    }
  }
  if (label === "Fungal disease risk") {
    return {
      severity,
      what: "High humidity together with rain expected.",
      why: "These conditions favor fungal disease spread on standing crops.",
      action: "Monitor crops closely for symptoms; consider a preventive fungicide.",
    }
  }
  return {
    severity,
    what: "No significant weather risk.",
    why: "Conditions are within normal range for the day.",
    action: "Continue normal farm operations.",
  }
}

/**
 * Per-category forecast risk, mirroring src/analytics.py's
 * compute_forecast_risk_for_row() exactly -- same thresholds, same
 * "derived_assessment" (rule-based, not ML) classification, same honest
 * "no threshold exists" gap for wind. That endpoint only exists per-plot
 * (/plots/{id}/analytics); this is the client-side mirror for the
 * Forecast page, which works from a Gram Panchayat alone with no plot
 * required -- same interim-mirror pattern as classifyForecastRow above.
 */
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"

export interface ForecastRiskCategory {
  level: RiskLevel
  label: string
}

export interface ForecastRiskBreakdown {
  heavy_rain_risk: ForecastRiskCategory
  heat_risk: ForecastRiskCategory
  humidity_risk: ForecastRiskCategory
  wind_risk: ForecastRiskCategory
}

function riskLevel(value: number | null | undefined, lowMax: number, highMin: number): RiskLevel {
  if (value == null) return "UNKNOWN"
  if (value <= lowMax) return "LOW"
  if (value > highMin) return "HIGH"
  return "MEDIUM"
}

export function computeForecastRiskForRow(row: Pick<ForecastRow, "rainfall_mm" | "temp_max_c" | "rh_max_pct">): ForecastRiskBreakdown {
  return {
    heavy_rain_risk: {
      level: riskLevel(row.rainfall_mm, HUMID_RAIN_THRESHOLD_MM, HEAVY_RAIN_THRESHOLD_MM),
      label: "Derived from forecast conditions",
    },
    heat_risk: {
      level: riskLevel(row.temp_max_c, HEAT_STRESS_THRESHOLD_C, HEAT_STRESS_THRESHOLD_C),
      label: "Derived from forecast conditions",
    },
    humidity_risk: {
      level: riskLevel(row.rh_max_pct, HUMID_RH_THRESHOLD_PCT, HUMID_RH_THRESHOLD_PCT),
      label: "Derived from forecast conditions",
    },
    // No wind-risk threshold has ever been established anywhere in this
    // project (src/analytics.py) -- stays honestly unclassified rather
    // than inventing a cutoff.
    wind_risk: { level: "UNKNOWN", label: "No wind-risk threshold is established in this system yet" },
  }
}

const RISK_ORDER: Record<RiskLevel, number> = { HIGH: 3, MEDIUM: 2, LOW: 1, UNKNOWN: 0 }

/** Worst case across a set of days, mirroring analytics.py's worst_case_risk(). */
export function worstCaseForecastRisk(rows: Pick<ForecastRow, "rainfall_mm" | "temp_max_c" | "rh_max_pct">[]): ForecastRiskBreakdown {
  const perDay = rows.map(computeForecastRiskForRow)
  const pick = (key: keyof ForecastRiskBreakdown) =>
    perDay.reduce((worst, d) => (RISK_ORDER[d[key].level] > RISK_ORDER[worst[key].level] ? d : worst), perDay[0])[key]
  return {
    heavy_rain_risk: pick("heavy_rain_risk"),
    heat_risk: pick("heat_risk"),
    humidity_risk: pick("humidity_risk"),
    wind_risk: pick("wind_risk"),
  }
}

/**
 * Rainfall outlook aggregated over the real forecast window, mirroring the
 * real-values-only approach of analytics.py's compute_rainfall_analytics
 * (no "rain probability" field exists anywhere in this pipeline, so it is
 * never shown/invented here).
 */
export interface RainfallOutlook {
  total_mm: number
  average_mm_per_day: number
  rainy_days: number
  total_days: number
  highest_day: { date: string; mm: number } | null
}

export function computeRainfallOutlook(rows: Pick<ForecastRow, "date" | "rainfall_mm">[]): RainfallOutlook | null {
  const withValues = rows.filter((r) => r.rainfall_mm != null) as { date: string; rainfall_mm: number }[]
  if (withValues.length === 0) return null
  const total = withValues.reduce((sum, r) => sum + r.rainfall_mm, 0)
  const rainyDays = withValues.filter((r) => r.rainfall_mm > 0).length
  const highest = withValues.reduce((max, r) => (r.rainfall_mm > max.rainfall_mm ? r : max), withValues[0])
  return {
    total_mm: Math.round(total * 10) / 10,
    average_mm_per_day: Math.round((total / withValues.length) * 100) / 100,
    rainy_days: rainyDays,
    total_days: withValues.length,
    highest_day: { date: highest.date, mm: highest.rainfall_mm },
  }
}

export interface FieldInspectionDecision {
  decision: "YES" | "DELAYED" | "MONITOR"
  priority: "HIGH" | "MEDIUM" | "LOW"
  why: string
  when: string
  points: string[]
}

/** Field Inspection Decision -- derived entirely from the already-real
 * `field_inspection` recommendation + disease/weather risk levels
 * farm_advisor.py already computed for a plot. Not a new decision engine, a
 * presentation-layer read of one. Shared by the Advisory page and the Farm
 * Overview page so the decision is computed in exactly one place. */
export function fieldInspectionDecision(advisor: FarmAdvisorResponse): FieldInspectionDecision | null {
  const rec = advisor.recommendations.find((r) => r.category === "field_inspection")
  if (!rec) return null

  const decision: FieldInspectionDecision["decision"] =
    rec.status === "recommended" ? "YES" : rec.status === "delay" || rec.status === "avoid" ? "DELAYED" : "MONITOR"
  const priority: FieldInspectionDecision["priority"] =
    rec.status === "recommended" ? "HIGH" : rec.status === "delay" || rec.status === "avoid" ? "MEDIUM" : "LOW"

  const points: string[] = []
  if (advisor.disease_risk.available && advisor.disease_risk.level && advisor.disease_risk.level !== "LOW") {
    points.push("Leaves (spots, discoloration, unusual lesions)", "Lower canopy / dense foliage")
  }
  if (rec.status === "delay" || rec.status === "avoid") {
    points.push("Wilting or heat-stress signs once conditions ease")
  }
  if (advisor.weather_risk.available && advisor.weather_risk.level === "HIGH") {
    points.push("Soil / root-zone drainage after rain")
  }
  if (points.length === 0) points.push("Routine check of leaves and stem for anything unusual")

  return { decision, priority, why: rec.why, when: rec.when, points }
}
