import { useQuery } from "@tanstack/react-query"
import { Leaf, Search as SearchIcon } from "lucide-react"
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"

import { EmptyState } from "@/components/EmptyState"
import { Input } from "@/components/ui/input"
import { getCropCatalog } from "@/lib/api"

const TOPICS = [
  { title: "Today's outlook", to: "/dashboard", keywords: ["weather", "today", "current"] },
  { title: "5-Day Forecast", to: "/forecast", keywords: ["forecast", "rain", "rainfall", "temperature"] },
  { title: "5-day advisory", to: "/advisory", keywords: ["advisory", "advice", "risk", "alert"] },
  { title: "My Farm", to: "/farm", keywords: ["farm", "crop", "field"] },
  { title: "Help & FAQ", to: "/help", keywords: ["help", "faq", "estimated", "confidence", "data source"] },
]

export function Search() {
  const [query, setQuery] = useState("")
  const { data: crops } = useQuery({ queryKey: ["crop-catalog"], queryFn: getCropCatalog })

  const q = query.trim().toLowerCase()

  const matchedTopics = useMemo(
    () => TOPICS.filter((t) => !q || t.title.toLowerCase().includes(q) || t.keywords.some((k) => k.includes(q))),
    [q]
  )
  const matchedCrops = useMemo(
    () => (crops ?? []).filter((c) => !q || c.name.toLowerCase().includes(q)),
    [crops, q]
  )

  const hasResults = matchedTopics.length > 0 || matchedCrops.length > 0

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-2xl font-medium text-charcoal">Search</h1>

      <div className="relative">
        <SearchIcon className="absolute left-4 top-1/2 size-4 -translate-y-1/2 text-pewter" aria-hidden="true" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search crops, forecast, advisory, help topics..."
          className="pl-11"
          autoFocus
        />
      </div>

      {!hasResults ? (
        <EmptyState message={`No results for "${query}".`} />
      ) : (
        <div className="space-y-6">
          {matchedCrops.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-medium text-graphite">Crops</h2>
              <div className="flex flex-wrap gap-2">
                {matchedCrops.map((crop) => (
                  <Link
                    key={crop.name}
                    to="/farm"
                    className="flex items-center gap-1.5 rounded-nav-pill bg-sage-card px-4 py-2 text-sm text-forest-ink"
                  >
                    <Leaf className="size-3.5" /> {crop.name}
                  </Link>
                ))}
              </div>
            </div>
          )}

          {matchedTopics.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-medium text-graphite">Pages</h2>
              <div className="space-y-2">
                {matchedTopics.map((topic) => (
                  <Link
                    key={topic.to}
                    to={topic.to}
                    className="block rounded-card bg-card p-4 text-sm text-charcoal hover:bg-ash-gray/60"
                  >
                    {topic.title}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
