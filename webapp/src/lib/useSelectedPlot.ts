import { useQueries, useQuery } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import { listFarms, listPlots, type Farm, type Plot } from "@/lib/api"

export interface SelectablePlot extends Plot {
  farm_name: string
}

/** Which Plot the Advisory page (and eventually other plot-scoped views)
 * shows -- mirrors lib/useSelectedGp.ts's exact pattern (localStorage-backed,
 * defaults to the first available option) since no equivalent "current
 * plot" state existed anywhere in the app before this. */
export function useSelectedPlot() {
  const { data: farms } = useQuery({ queryKey: ["farms"], queryFn: listFarms })
  const plotQueries = useQueries({
    queries: (farms ?? []).map((farm: Farm) => ({
      queryKey: ["plots", farm.id],
      queryFn: () => listPlots(farm.id),
    })),
  })

  const isLoading = farms === undefined || plotQueries.some((q) => q.isLoading)
  const farmNameById = new Map((farms ?? []).map((f) => [f.id, f.name]))
  const plots: SelectablePlot[] = plotQueries.flatMap((q) =>
    (q.data ?? []).map((plot) => ({ ...plot, farm_name: farmNameById.get(plot.farm_id) ?? "" }))
  )

  const [selected, setSelected] = useState<string>(() => localStorage.getItem("selected_plot_id") ?? "")

  useEffect(() => {
    if (!isLoading && !plots.some((p) => p.id === selected) && plots.length > 0) {
      setSelected(plots[0].id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, plots.length, selected])

  const select = (plotId: string) => {
    setSelected(plotId)
    localStorage.setItem("selected_plot_id", plotId)
  }

  return {
    farms: farms ?? [],
    plots,
    selectedPlotId: plots.some((p) => p.id === selected) ? selected : "",
    selectPlot: select,
    isLoading,
  }
}
