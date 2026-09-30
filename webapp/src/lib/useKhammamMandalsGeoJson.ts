import { useQuery } from "@tanstack/react-query"

export interface MandalFeature {
  type: "Feature"
  properties: { mandal: string; district: string; state: string }
  geometry: GeoJSON.Geometry
}

export interface MandalFeatureCollection {
  type: "FeatureCollection"
  features: MandalFeature[]
}

async function fetchKhammamMandals(): Promise<MandalFeatureCollection> {
  const res = await fetch("/data/khammam_mandals.geojson")
  if (!res.ok) throw new Error("Failed to load mandal boundary data")
  return res.json()
}

/** Real public mandal/block boundary data for Khammam district (see
 * lib/telanganaLocations.ts for source + the pre/post-2016 boundary
 * caveat). Only district currently fetched -- see docs/FOUNDATION.md-style
 * honesty: other districts show "boundary data unavailable" rather than a
 * silently-empty or fabricated map. */
export function useKhammamMandalsGeoJson() {
  return useQuery({
    queryKey: ["khammam-mandals-geojson"],
    queryFn: fetchKhammamMandals,
    staleTime: Infinity,
  })
}
