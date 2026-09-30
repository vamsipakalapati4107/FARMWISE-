import { ArrowRight, CloudSun, MapPin, Sprout, Stethoscope } from "lucide-react"
import { Link } from "react-router-dom"

import { FieldPattern } from "@/components/FieldPattern"
import { LanguageSelector } from "@/components/LanguageSelector"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const FEATURES = [
  { icon: MapPin, title: "Localized Weather", body: "Forecasts downscaled to your Gram Panchayat, not just the block." },
  { icon: Stethoscope, title: "Crop Advisory", body: "Plain-language, crop-stage-aware recommendations." },
  { icon: CloudSun, title: "Weather Alerts", body: "Heavy rain, heat stress, and fungal-risk warnings." },
  { icon: Sprout, title: "Farm Management", body: "Track your farms and crops in one place." },
]

const STEPS = ["Choose Location", "Get Local Weather", "Add Your Crop", "Receive Farm Advisory"]

export function Landing() {
  return (
    <div className="min-h-screen bg-bone">
      {/* Marquee strip -- the one place vivid lime appears, per DESIGN.md */}
      <div className="overflow-hidden whitespace-nowrap bg-vivid-lime py-2 text-xs font-medium text-charcoal">
        <span className="inline-block animate-[marquee_28s_linear_infinite]">
          {Array.from({ length: 4 })
            .map(
              () =>
                "✓ Village-level forecasts for Sathupally block" +
                "    " +
                "✓ Plain-language crop advisories" +
                "    "
            )
            .join("")}
        </span>
      </div>
      <style>{`@keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }`}</style>

      <header className="flex items-center justify-between bg-forest-ink px-6 py-4 text-white">
        <div className="flex items-center gap-2 font-serif text-lg">
          <Sprout className="size-5 text-vivid-lime" /> FarmWise
        </div>
        <div className="flex items-center gap-2">
          <LanguageSelector variant="on-dark" />
          <Link to="/login" className={cn(buttonVariants({ variant: "outline" }), "border-white/40 text-white")}>
            Log in
          </Link>
          <Link to="/register" className={buttonVariants({ variant: "secondary" })}>
            Get Started
          </Link>
        </div>
      </header>

      {/* Full-bleed hero -- FieldPattern stands in for photography (see its own docstring) */}
      <section className="relative flex min-h-[80vh] items-center justify-center overflow-hidden text-center">
        <FieldPattern className="absolute inset-0 h-full w-full" />
        <div className="absolute inset-0 bg-forest-ink/10" />
        <div className="relative z-10 mx-auto max-w-3xl px-6 py-24">
          <h1 className="font-serif text-4xl font-light text-white sm:text-6xl" style={{ letterSpacing: "-0.012em" }}>
            Weather intelligence and actionable farm advisories, designed for every farmer.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-white/85">
            Village-level weather forecasts and plain-language advisories for Sathupally block,
            Khammam district — downscaled from block-level data to your Gram Panchayat.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Link to="/register" className={buttonVariants({ size: "lg" })}>
              Get Started
            </Link>
            <Link
              to="/login"
              className={cn(buttonVariants({ size: "lg", variant: "outline" }), "border-white/60 text-white")}
            >
              Log in
            </Link>
          </div>
          <p className="mt-10 text-xs text-white/70">Scroll to explore ↓</p>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto grid max-w-5xl grid-cols-1 gap-6 px-6 py-20 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map(({ icon: Icon, title, body }, i) => {
          const tones = ["bg-sky-card", "bg-peach-card", "bg-sage-card", "bg-ash-gray"]
          return (
            <div key={title} className={cn("rounded-card p-6", tones[i % tones.length])}>
              <Icon className="mb-3 size-6 text-forest-ink" />
              <h3 className="mb-1 font-serif text-lg text-charcoal">{title}</h3>
              <p className="text-sm text-graphite">{body}</p>
            </div>
          )
        })}
      </section>

      {/* How it works -- forest interstitial band */}
      <section className="bg-forest-ink px-6 py-20 text-white">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="font-serif text-3xl font-light">How it works</h2>
          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
            {STEPS.map((step, i) => (
              <div key={step} className="flex items-center gap-4">
                <div className="flex flex-col items-center gap-2">
                  <span className="flex size-10 items-center justify-center rounded-full bg-white/15 font-serif text-lg">
                    {i + 1}
                  </span>
                  <span className="text-sm text-white/90">{step}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <ArrowRight className="hidden size-5 text-white/40 sm:block" aria-hidden="true" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="bg-forest-ink px-6 py-10 text-center text-xs text-white/60">
        <p>FarmWise — SIH 26074, Sathupally block, Khammam district, Telangana.</p>
      </footer>
    </div>
  )
}
