import { useQuery } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import { getGps } from "@/lib/api"

/** Which Gram Panchayat the dashboard/forecast/advisory pages show. Backed by
 * localStorage for now; once a user has a Farm (Phase 8 API, Phase 10 UI),
 * onboarding sets this from their farm's gram_panchayat. */
export function useSelectedGp() {
  const { data: gps } = useQuery({ queryKey: ["gps"], queryFn: getGps })
  const [selected, setSelected] = useState<string>(() => localStorage.getItem("selected_gp") ?? "")

  useEffect(() => {
    if (!selected && gps && gps.length > 0) {
      setSelected(gps[0].gram_panchayat)
    }
  }, [gps, selected])

  const select = (gpName: string) => {
    setSelected(gpName)
    localStorage.setItem("selected_gp", gpName)
  }

  return { gps: gps ?? [], selectedGp: selected, selectGp: select }
}
