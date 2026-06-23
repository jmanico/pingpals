/**
 * Pingpals design tokens — single source of truth (REQ-FND-005, DESIGN.md §3/§4/§7.1).
 *
 * Every styled component MUST consume these tokens and MUST NOT hard-code color/size/spacing
 * literals (DESIGN.md §7.1, CLAUDE.md "design tokens only"). Hex values are PROVISIONAL — sampled
 * from the raster logo and pending a color-pick against vector source art (DESIGN.md §9). They are
 * defined here by name now; locking exact hex later requires no component change.
 *
 * Accessibility (DESIGN.md §3.4, NFR-1.4 / WCAG 2.2 AA): `bodyTextOnBackground` enumerates the
 * ONLY approved body-text/background pairings; all meet >= 4.5:1. Royal Gold on cream FAILS
 * contrast and is therefore absent from that list — gold is trim/icon/large-accent only, never
 * body copy on a light surface. `tokens.test.ts` enforces both facts.
 */

/** Core brand palette (DESIGN.md §3.1). */
export const color = {
  purple900: "#2E1259", // Plum Ink — wordmark, primary text on light, deepest shade
  purple700: "#4B1E83", // Royal Purple — primary brand, throne, primary buttons
  purple500: "#6B3FA0", // Amethyst — secondary accents, gems, hover states
  gold500: "#E2A52B", // Royal Gold — crown, dividers, key accents (ACCENT, not body text)
  gold300: "#F4C95D", // Gilt — highlights, gradients, focus glows / focus ring
  cream50: "#F6F1E7", // Parchment — primary background
  white: "#FFFFFF", // Ermine White — surfaces, cards
  ink900: "#1C1430", // Court Ink — fine detail, max-contrast text
} as const;

/** Semantic status colors (DESIGN.md §3.3). Status is never conveyed by color alone (§3.4). */
export const semantic = {
  success: "#2E7D5B", // contacted / on-cadence
  warning: "#E2A52B", // due soon (Royal Gold)
  danger: "#B23A48", // overdue / destructive
  info: "#6B3FA0", // neutral notice (Amethyst)
} as const;

/** Type scale in rem (DESIGN.md §4.2). */
export const typeScale = {
  display: "2.5rem",
  h1: "2rem",
  h2: "1.5rem",
  h3: "1.25rem",
  body: "1rem",
  small: "0.875rem",
  caption: "0.75rem",
} as const;

/** Font families (DESIGN.md §4) — self-hosted SIL OFL faces, robust system fallbacks (FE-1.4). */
export const fontFamily = {
  display: '"Cinzel", Georgia, "Times New Roman", serif',
  heading: '"Playfair Display", Georgia, serif',
  body: '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  accent: '"Poppins", system-ui, sans-serif',
} as const;

/** Spacing scale (rem). */
export const spacing = {
  xs: "0.25rem",
  sm: "0.5rem",
  md: "1rem",
  lg: "1.5rem",
  xl: "2rem",
  xxl: "3rem",
} as const;

/** Corner radii (rem) — echoing the throne's rounded forms (DESIGN.md §7). */
export const radius = {
  sm: "0.25rem",
  md: "0.5rem",
  lg: "1rem",
  pill: "999px",
} as const;

/**
 * Approved body-text-on-background pairings (DESIGN.md §3.4, normative). Each MUST meet WCAG 2.2
 * AA body contrast (>= 4.5:1). Royal Gold on cream is intentionally NOT here (it fails).
 */
export const bodyTextOnBackground: ReadonlyArray<{
  readonly text: string;
  readonly background: string;
}> = [
  { text: color.purple900, background: color.cream50 }, // default high-contrast body pairing
  { text: color.purple900, background: color.white },
  { text: color.ink900, background: color.cream50 },
  { text: color.white, background: color.purple700 }, // light text on deep purple
] as const;

export const tokens = {
  color,
  semantic,
  typeScale,
  fontFamily,
  spacing,
  radius,
  bodyTextOnBackground,
} as const;

export default tokens;
