import { useQuery } from "@tanstack/react-query"

export interface DistrictFeature {
  type: "Feature"
  properties: { district: string; dt_code: string; st_nm: string; year: string }
  geometry: GeoJSON.Geometry
}

export interface DistrictFeatureCollection {
  type: "FeatureCollection"
  features: DistrictFeature[]
}

async function fetchTelanganaDistricts(): Promise<DistrictFeatureCollection> {
  const res = await fetch("/data/telangana_districts.geojson")
  if (!res.ok) throw new Error("Failed to load district boundary data")
  return res.json()
}

/** Real public district boundary data (see lib/telanganaLocations.ts for
 * source attribution) -- fetched once and cached, not bundled into the JS
 * chunk (it's ~570KB of real polygon geometry). */
export function useTelanganaGeoJson() {
  return useQuery({
    queryKey: ["telangana-districts-geojson"],
    queryFn: fetchTelanganaDistricts,
    staleTime: Infinity, // static reference data, never changes at runtime
  })
}
