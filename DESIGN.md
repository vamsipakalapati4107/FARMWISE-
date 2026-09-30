# Design System — Sathupally Farmer Platform

Adapted from the "Arva" pastoral-editorial style reference. Arva is already an
agriculture-facing brand, so its tokens are kept close to verbatim rather than
reinterpreted. What's *not* carried over: Arva's marketing-site components
(full-bleed hero photography, lime marquee strip, partner-logo cards,
testimonial quilts) — this app is a farmer dashboard, not a landing site, so
only the Landing page (Phase 10) uses those; the rest of the app is
information-dense screens the base tokens and cards support directly.

**One deliberate addition beyond Arva:** a status/severity sub-palette. Arva's
own rule is "no saturated colors beyond Forest Ink and Vivid Lime" — correct
for a marketing site, but this app has a safety-critical need Arva's reference
doesn't cover: a farmer must be able to tell "heavy rain warning" from "normal"
at a glance. The status colors below are kept muted and earth-toned (a clay
terracotta, not a stop-sign red) so they read as an extension of the palette,
not a break from it.

## Colors

```css
:root {
  /* Core Arva palette */
  --color-forest-ink: #07503f;   /* brand, header, section bands, primary buttons */
  --color-vivid-lime: #e8fe85;   /* single high-energy accent — use sparingly */
  --color-bone: #f1efdf;         /* page canvas — never pure white */
  --color-pure-white: #ffffff;   /* card surfaces, inputs, button text */
  --color-ash-gray: #efefef;     /* secondary card surface, dividers */
  --color-charcoal: #212529;     /* primary text */
  --color-graphite: #353535;     /* secondary text, borders */
  --color-pewter: #6d6d6d;       /* muted/helper text */
  --color-sky-card: #b2cee7;     /* pastel tile */
  --color-peach-card: #fceace;   /* pastel tile */
  --color-sage-card: #e6ecd5;    /* pastel tile */
  --color-moss: #c3cda7;         /* borders, input outlines */

  /* Status sub-palette (new — see note above) */
  --color-status-critical: #b3532f;   /* muted terracotta — heavy rain, extreme heat */
  --color-status-critical-bg: #f3e2d8;
  --color-status-warning: #c9922b;    /* muted amber — fungal risk, wind advisories */
  --color-status-warning-bg: #f5ecd8;
  --color-status-safe: #4a7a5e;       /* muted forest-sage — normal operations */
  --color-status-safe-bg: var(--color-sage-card);
  --color-status-info: #3d6b8c;       /* muted slate blue — informational only */
  --color-status-info-bg: var(--color-sky-card);
}
```

Dark mode is out of scope for v1 (farmer-facing outdoor daytime use case).

## Typography

- **Reckless** (serif, weights 300/500/600) — headlines and section titles,
  24px and above only. Substitute: Cormorant Garamond or Source Serif Pro if
  no licensed Reckless file is available.
- **Inter** (sans, weights 400–600) — everything else: body, UI, forms, nav,
  badges. Never Reckless below 24px, never centered body paragraphs (max
  60ch, left-aligned).

| Role | Family | Weight | Size | Line height |
|---|---|---|---|---|
| caption | Inter | 400 | 12px | 1.5 |
| body-sm | Inter | 400 | 14px | 1.5 |
| body | Inter | 400 | 16px | 1.52 |
| subheading | Reckless | 500 | 24px | 1.24 |
| heading-sm | Reckless | 500 | 37px | 1.22 |
| heading | Reckless | 300/500 | 45px | 1.06 |
| heading-lg | Reckless | 300 | 57px | 1.06 |

## Spacing & Shape

Comfortable density. Section gap 50px, card padding 30px, element gap 8px.

**Radii are large and non-negotiable:**
- Cards: 20px
- Inputs: 33px
- Buttons: 100px (pill)
- Nav pills: 110px

**No box-shadows anywhere.** Elevation comes from surface color shifts only:
bone canvas (0) → white or pastel card (1) → forest-ink band (2, dark
interstitial sections like the header/footer).

## Components (dashboard-specific, beyond the Arva marketing set)

- **WeatherCard**: white surface, 20px radius, 30px padding, no shadow.
- **AdvisoryCard / WeatherAlert**: uses the status sub-palette — a colored
  left border (4px, status color) + tinted background (status `-bg` token),
  never color alone (icon + text label always present too, for accessibility).
- **Pill buttons**: `--color-forest-ink` fill / white text for primary,
  1px `--color-graphite` outline / transparent fill for secondary — both
  100px radius, 10px 24px padding, Inter 500 14px.
- **Pastel quilt cards**: rotate sky/peach/sage/bone per row (never mix two
  pastels in one card) — used for crop cards and category tiles, one surface
  color per tile.

## Do's and Don'ts (carried from Arva, apply here too)

- Do use `--color-bone` as canvas on every light section, never pure white.
- Do apply the pill radius to every button and nav element without exception.
- Do pair Reckless headlines with Inter body — that tension is the brand voice.
- Do let vivid lime appear only as a rare promotional accent (Landing page CTA
  ribbon), never in the main app.
- Don't use small radii (4–8px) on any button or card.
- Don't add shadows/elevation via `box-shadow` — use surface color instead.
- Don't introduce new saturated hues beyond the status sub-palette above.
- Don't center body paragraphs.
