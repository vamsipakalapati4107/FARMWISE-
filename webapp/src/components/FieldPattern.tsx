/**
 * Abstract "fields seen from altitude" backdrop -- stands in for the
 * full-bleed agricultural photography DESIGN.md calls for. We have no
 * licensed photography to use, so this is an original SVG pattern instead
 * of an unlicensed stock photo, in the same forest/sage/moss palette.
 */
export function FieldPattern({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 400 300"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="field-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0a6650" />
          <stop offset="100%" stopColor="#07503f" />
        </linearGradient>
      </defs>
      <rect width="400" height="300" fill="url(#field-sky)" />
      {Array.from({ length: 9 }).map((_, i) => (
        <path
          key={i}
          d={`M -20 ${20 + i * 34} Q 200 ${i * 34 + (i % 2 === 0 ? 60 : 0)} 420 ${20 + i * 34}`}
          fill="none"
          stroke={i % 3 === 0 ? "#c3cda7" : "#e6ecd5"}
          strokeOpacity={i % 3 === 0 ? 0.35 : 0.2}
          strokeWidth={10}
        />
      ))}
    </svg>
  )
}
