# Pingpals: DESIGN.md

**Project:** Pingpals (personal relationship cadence and reminder system)
**Document:** DESIGN.md — Brand & Visual Design System
**Version:** 0.1.0
**Status:** Draft
**Companion document:** [REQUIREMENTS.md](./REQUIREMENTS.md)

> This document defines the visual identity, design language, and UI guidance for Pingpals. It is derived from the primary logo (`assets/pingpals-logo.png`) and is the source of truth for brand decisions. Where it touches the product UI, it defers to the security and accessibility constraints in [REQUIREMENTS.md](./REQUIREMENTS.md) (Section 9, Frontend; NFR-1.4, WCAG 2.2 AA).

---

## 1. Brand essence

Pingpals turns an everyday chore — staying in touch — into something that feels effortless and a little regal. The mascot, **King Ping** (a crowned smartphone on a throne), embodies the core promise: you are the king of your relationships, and Pingpals is the loyal court that reminds you to hold your subjects close.

- **Personality:** regal, warm, witty, premium-but-approachable.
- **Promise:** _"Because even kings forget to text back."_
- **Feeling:** the calm confidence of having a butler who never lets a birthday slip.

**Tone in three words:** Noble. Playful. Reassuring.

---

## 2. Logo

The primary lockup pairs the **King Ping mascot** (a smartphone with closed eyes, mustache, and crown, seated on a gold-trimmed royal-purple throne with an ermine cape) with the **"PING / PALS" wordmark** in a high-contrast serif, divided by a small gold crown, above the tagline.

### 2.1 Logo variants

| Variant | Use |
| --- | --- |
| **Primary lockup** (mascot + wordmark + tagline) | Marketing, landing page, README hero, app splash. |
| **Horizontal lockup** (mascot + wordmark, no tagline) | Headers, navigation bars, email headers. |
| **Mascot mark** (King Ping alone) | App icon, favicon, avatar, notification badge, loading states. |
| **Wordmark only** | Footers, legal pages, contexts too small for the mascot. |

> MVP ships the primary lockup and the mascot mark. Other variants are produced as needed.

### 2.2 Clear space and minimum size

- **Clear space:** maintain padding equal to the height of the crown on the wordmark divider on all sides. Nothing else intrudes into this zone.
- **Minimum size:** primary lockup no smaller than 160 px wide; mascot mark no smaller than 24 px (favicon) and should be re-drawn as a simplified silhouette below 32 px.

### 2.3 Logo don'ts

- Do **not** recolor the mascot or wordmark outside the approved palette.
- Do **not** stretch, skew, rotate, or add drop shadows/glows beyond the soft contact shadow in the source art.
- Do **not** place the logo on a low-contrast or busy background; use the cream or a solid brand color with sufficient contrast.
- Do **not** reconstruct the wordmark in a different typeface.

---

## 3. Color palette

Colors are sampled from the logo and expressed as design tokens. Hex values are the canonical reference; **confirm exact values against the source art with a color picker before production use** and lock them into the token file.

### 3.1 Core brand

| Token | Name | Hex (approx.) | Role |
| --- | --- | --- | --- |
| `--color-purple-900` | Plum Ink | `#2E1259` | Wordmark, primary text on light, deepest shade. |
| `--color-purple-700` | Royal Purple | `#4B1E83` | Primary brand color, throne, primary buttons. |
| `--color-purple-500` | Amethyst | `#6B3FA0` | Secondary accents, gems, hover states. |
| `--color-gold-500` | Royal Gold | `#E2A52B` | Secondary brand color, crown, dividers, key accents. |
| `--color-gold-300` | Gilt | `#F4C95D` | Gold highlights, gradients, focus glows. |
| `--color-cream-50` | Parchment | `#F6F1E7` | Primary background. |
| `--color-white` | Ermine White | `#FFFFFF` | Surfaces, cards, the mascot's "face." |
| `--color-ink-900` | Court Ink | `#1C1430` | Ermine spots, fine detail, max-contrast text. |

### 3.2 Usage rules

- **Purple is the lead.** Gold is the **accent** — used sparingly for emphasis (royalty earns its shine). Avoid large gold fills; gold is trim, not upholstery.
- **Cream is the canvas.** Default backgrounds are Parchment, not pure white, to carry the premium/aged-paper warmth.
- **One royal pairing per surface.** Purple + gold is the signature; don't dilute it with competing accent hues.

### 3.3 Semantic colors

Derive status colors that sit harmoniously beside the royal palette:

| Token | Role | Hex (approx.) |
| --- | --- | --- |
| `--color-success` | Contacted / on-cadence | `#2E7D5B` |
| `--color-warning` | Due soon | `#E2A52B` (Royal Gold) |
| `--color-danger` | Overdue / destructive | `#B23A48` |
| `--color-info` | Neutral notice | `#6B3FA0` (Amethyst) |

### 3.4 Accessibility (normative)

- All text/background pairings **MUST** meet WCAG 2.2 AA contrast (4.5:1 body, 3:1 large text / UI), per REQUIREMENTS.md **NFR-1.4**.
- Plum Ink (`#2E1259`) on Parchment (`#F6F1E7`) is the default high-contrast pairing for body text.
- **Gold text on cream fails contrast** — never use Royal Gold for body copy on light backgrounds. Use it for shapes, borders, and icons, or as text only on deep purple.
- Color **MUST NOT** be the sole means of conveying status (e.g., overdue): pair color with an icon and/or label.

---

## 4. Typography

The logo uses a classical, high-contrast serif for the wordmark and a clean humanist sans-serif for the tagline. The type system mirrors that contrast: a regal display serif for moments of brand voice, a neutral sans-serif for the working UI.

| Role | Typeface (recommended) | Notes |
| --- | --- | --- |
| **Display / wordmark** | Cinzel (or Trajan Pro) | All-caps, classical Roman serif matching the logo. Headlines, hero, brand moments only. |
| **Headings** | Playfair Display | High-contrast serif; warmer than the all-caps display for in-product headings. |
| **Body / UI** | Inter | Highly legible, variable, excellent at small sizes; the workhorse for app text. |
| **Accent / friendly** | Poppins | Optional rounded geometric sans for the tagline and playful microcopy. |

### 4.1 Type rules

- Display serif is **all caps with generous letter-spacing**, used sparingly — it is seasoning, not body copy.
- Body text is sentence case, Inter, with comfortable line-height (≈1.5) for readability.
- Use web fonts loaded with Subresource Integrity per REQUIREMENTS.md **FE-1.8**, or self-host to satisfy the strict CSP (**FE-1.4**). Provide robust system-font fallbacks.

### 4.2 Suggested type scale (rem)

`2.5` (display) · `2.0` (h1) · `1.5` (h2) · `1.25` (h3) · `1.0` (body) · `0.875` (small) · `0.75` (caption).

---

## 5. Iconography and motifs

The brand has three recurring motifs drawn from the logo. Use them to make the product unmistakably Pingpals.

- **The crown** — the signature accent. A small gold crown is the brand's "bullet" / divider and the marker for premium or "royal" actions. Use as section dividers (crown flanked by thin gold rules) echoing the wordmark.
- **The speech bubble** — the purple "`...`" bubble represents a pending ping/conversation. Reuse for notifications, the reminder badge, and chat/outreach affordances.
- **King Ping** — the mascot anchors empty states, onboarding, and celebratory moments (e.g., "Long live the streak!" when a contact is logged on time).

**Icon style:** rounded, friendly, slightly weighty strokes to match the mascot. Single-color (Plum Ink or Royal Purple) for UI icons; reserve gold for accent/premium icons. Never build icons from untrusted strings; all rendered SVG follows the output-handling rules in REQUIREMENTS.md (**FE-1.1**, **SEC-4.2**).

---

## 6. Voice and tone

The copy carries the regal-but-playful personality. The tagline _"Because even kings forget to text back."_ sets the register.

- **Be the loyal advisor, not the nag.** Reminders are gentle nudges with a wink, never guilt trips.
- **Lean into the royal metaphor, lightly.** "Your court," "subjects," "the royal reminder," "long live the streak" — a sprinkle, not a costume.
- **Be concise and warm.** Short, human sentences. Respect the user's time as you'd respect a monarch's.

**Examples**

- Reminder: _"Your Majesty, it's been a while since you pinged Alex. Send word?"_
- Empty state: _"The court is quiet. Add your first pal to begin your reign."_
- Success: _"Decreed and done. Alex has been pinged. 👑"_
- Error (gentle, never blaming): _"That didn't go through. The royal messenger will try again."_

> Microcopy still follows the product's reject-over-sanitize input rules (REQUIREMENTS.md **FR-1.4**) — playful tone never softens a validation error into ambiguity.

---

## 7. UI application

Translating the brand into the React 19 frontend (REQUIREMENTS.md Section 9):

- **Surfaces:** Parchment background, white cards with soft shadows and gently rounded corners (echoing the throne's rounded forms).
- **Primary action:** Royal Purple (`--color-purple-700`) button, Ermine White label; hover to Amethyst. Gold reserved for a single hero/premium CTA per view.
- **Focus state:** a Gilt (`#F4C95D`) focus ring — visible, on-brand, and meeting the 3:1 non-text contrast requirement. Never remove focus outlines.
- **Reminder card:** speech-bubble motif, contact display name, chosen channel, and the one-tap outreach action only — matching the minimal reminder payload in REQUIREMENTS.md **FR-5.4**. Outreach links pass `validateAndSanitizeUrl` (**FE-1.3**, **FR-6.4**) and render `#` if invalid.
- **Density:** generous spacing; this is a calm, premium product, not a dense dashboard.

### 7.1 Design tokens

Ship the palette, type scale, spacing, and radii as a single source-of-truth token file (e.g., CSS custom properties / a `tokens.ts`). Components consume tokens, never hard-coded values, so rebranding and theming stay centralized.

---

## 8. Assets

| Asset | Path | Notes |
| --- | --- | --- |
| Primary logo (raster) | `assets/pingpals-logo.png` | 1448×1086 source lockup. |

**Backlog (to produce):**

- Vector (SVG) versions of the wordmark, mascot mark, and primary lockup for crisp scaling.
- App icon / favicon set derived from the mascot mark.
- Monochrome and reversed (on-purple) logo variants.
- A finalized, color-picked token file locking exact hex values.

---

## 9. Open questions

- **Exact brand hex values:** the palette above is sampled approximately from the raster logo and must be confirmed against vector source art.
- **Font licensing:** confirm licensing for Cinzel/Trajan/Playfair/Inter/Poppins for web and app embedding, or finalize self-hosted equivalents.
- **Mascot expression set:** decide whether King Ping gets multiple expressions (sleeping, alert, celebrating) for use across states.
- **Dark mode:** define a royal dark theme (deep purple canvas, gold/cream text) once the light system is locked.
