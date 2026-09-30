/**
 * Standard NOAA/Rothfusz heat-index approximation, derived from real
 * temperature + humidity (not invented) -- a legitimate meteorological
 * derivation, same as any weather app's "feels like". This is a display-only
 * formula so it stays client-side; the hourly-estimated curve, by contrast,
 * is computed server-side (src/routers/weather.py) so it has one source of
 * truth shared by every client.
 */
export function computeFeelsLikeC(tempC: number, relativeHumidityPct: number): number {
  const tempF = (tempC * 9) / 5 + 32
  if (tempF < 80) return tempC // Rothfusz regression is only valid above ~80°F
  const rh = relativeHumidityPct

  const hiF =
    -42.379 +
    2.04901523 * tempF +
    10.14333127 * rh -
    0.22475541 * tempF * rh -
    0.00683783 * tempF * tempF -
    0.05481717 * rh * rh +
    0.00122874 * tempF * tempF * rh +
    0.00085282 * tempF * rh * rh -
    0.00000199 * tempF * tempF * rh * rh

  return Math.round((((hiF - 32) * 5) / 9) * 10) / 10
}
