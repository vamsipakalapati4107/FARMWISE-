import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

const FAQS = [
  {
    q: "Where does the weather data come from?",
    a: "Forecasts start from the Sathupally block-level weather forecast, then are statistically downscaled to your specific Gram Panchayat using ERA5-Land reanalysis data and each village's elevation and distance from the nearest weather grid cell.",
  },
  {
    q: "Why does the forecast only cover 5 days?",
    a: "That's the real horizon of the block-level forecast we downscale from. We don't invent additional days beyond what's actually forecast.",
  },
  {
    q: "What does \"Estimated\" mean next to the hourly chart?",
    a: "We only have a day's minimum and maximum temperature, not real hour-by-hour sensor readings. The hourly view interpolates a plausible curve between those two real numbers so you can see a shape, not a sensor reading — hence the label.",
  },
  {
    q: "What does the confidence level (high/medium) mean?",
    a: "It reflects how close your Gram Panchayat is to the weather grid cell used for downscaling. Closer villages get \"high\" confidence; farther ones get \"medium\".",
  },
  {
    q: "How is my crop-specific advisory different from the general weather advisory?",
    a: "The general advisory only looks at rainfall, temperature, and humidity thresholds. The crop-specific version also factors in your crop and its current growth stage — for example, rain during cotton's flowering stage carries a boll-rot warning that a generic rain alert wouldn't mention.",
  },
  {
    q: "Is my data shared with anyone?",
    a: "No. Your account, farms, and crops are stored only for showing you your own dashboard.",
  },
]

export function Help() {
  return (
    <div className="space-y-6">
      <h1 className="font-serif text-2xl font-medium text-charcoal">Help &amp; FAQ</h1>
      <div className="rounded-card bg-card p-6">
        <Accordion>
          {FAQS.map((faq, i) => (
            <AccordionItem key={faq.q} value={`item-${i}`}>
              <AccordionTrigger className="text-left font-medium text-charcoal">{faq.q}</AccordionTrigger>
              <AccordionContent className="text-graphite">{faq.a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </div>
  )
}
