/**
 * Real reference geographic data for the State -> District -> Block/Mandal
 * -> Panchayat picker. This project's downscaled forecast pipeline only
 * covers Khammam district / Sathupally block / its 21 real Gram
 * Panchayats (see docs/FOUNDATION.md) -- everywhere else in this file is
 * real place names with NO forecast data behind them, and the UI must say
 * so rather than hide or fake it.
 *
 * Sources (public, open data -- not fabricated):
 * - District names + polygons: public/data/telangana_districts.geojson,
 *   from udit-001/india-maps-data (github.com/udit-001/india-maps-data),
 *   33 districts, 2016 reorganization.
 * - Mandal names for Khammam: gggodhwani/telangana_boundaries
 *   (github.com/gggodhwani/telangana_boundaries), which uses the PRE-2016
 *   (10-district) Khammam boundary -- so a handful of these 41 mandals
 *   (e.g. Bhadrachalam, Kothagudem, Manuguru, Palwancha) are now actually
 *   part of Bhadradri Kothagudem district post-2016, not modern Khammam.
 *   Kept as-is with this caveat rather than silently "corrected" without a
 *   verified post-2016 mandal-to-district mapping.
 */

export const STATE = "Telangana"

/** All 33 real Telangana districts (2016 boundaries) -- only Khammam has
 * real pipeline data behind it. */
export const TELANGANA_DISTRICTS_WITH_DATA = ["Khammam"] as const

/** Real Khammam-area mandal names (see source caveat above). Only
 * Sathupally has a real downscaled forecast. */
export const KHAMMAM_MANDALS = [
  "Aswapuram",
  "Aswaraopeta",
  "Bayyaram",
  "Bhadrachalam",
  "Bonakal",
  "Burgampahad",
  "Chandrugonda",
  "Cherla",
  "Chinthakani",
  "Dammapeta",
  "Dummugudem",
  "Enkuru",
  "Garla",
  "Gundala",
  "Julurpad",
  "Kallur",
  "Kamepalle",
  "Khammam (Rural)",
  "Khammam (Urban)",
  "Konijerla",
  "Kothagudem",
  "Kusumanchi",
  "Madhira",
  "Manuguru",
  "Mudigonda",
  "Mulkalapalle",
  "Nelakondapalle",
  "Palwancha",
  "Penuballi",
  "Pinapaka",
  "Sathupally",
  "Singareni",
  "Tallada",
  "Tekulapalle",
  "Thirumalayapalem",
  "Vemsoor",
  "Venkatapuram",
  "Wazeed",
  "Wyra",
  "Yellandu",
  "Yerrupalem",
] as const

export const MANDAL_WITH_DATA = "Sathupally"

export function districtHasData(district: string): boolean {
  return (TELANGANA_DISTRICTS_WITH_DATA as readonly string[]).includes(district)
}

export function mandalHasData(mandal: string): boolean {
  return mandal === MANDAL_WITH_DATA
}
