/**
 * Design-token tests (REQ-FND-005).
 *
 * AC-01: all core brand, semantic, type-scale, spacing, and radius tokens are defined by name.
 * §3.4 (normative): every approved body-text pairing meets WCAG 2.2 AA (>= 4.5:1), and the known
 * failing pairing (Royal Gold on Parchment) is rejected as body text.
 */
import { describe, expect, it } from "vitest";

import { bodyTextOnBackground, color, radius, semantic, spacing, tokens, typeScale } from "./tokens";

/** WCAG 2.1 relative luminance + contrast ratio. */
function relativeLuminance(hex: string): number {
  const h = hex.replace("#", "");
  const channels = [0, 2, 4].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  const [r, g, b] = channels;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const [lighter, darker] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (lighter + 0.05) / (darker + 0.05);
}

describe("design tokens (REQ-FND-005 AC-01)", () => {
  it("defines all core brand color tokens by name", () => {
    for (const key of [
      "purple900",
      "purple700",
      "purple500",
      "gold500",
      "gold300",
      "cream50",
      "white",
      "ink900",
    ]) {
      expect(color).toHaveProperty(key);
      expect(color[key as keyof typeof color]).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
  });

  it("defines all semantic status tokens", () => {
    for (const key of ["success", "warning", "danger", "info"]) {
      expect(semantic).toHaveProperty(key);
    }
  });

  it("defines the full type scale, spacing, and radii", () => {
    for (const key of ["display", "h1", "h2", "h3", "body", "small", "caption"]) {
      expect(typeScale).toHaveProperty(key);
    }
    for (const key of ["xs", "sm", "md", "lg", "xl", "xxl"]) {
      expect(spacing).toHaveProperty(key);
    }
    for (const key of ["sm", "md", "lg", "pill"]) {
      expect(radius).toHaveProperty(key);
    }
  });

  it("exposes a single aggregated token object", () => {
    expect(tokens.color).toBe(color);
    expect(tokens.bodyTextOnBackground).toBe(bodyTextOnBackground);
  });
});

describe("accessibility — WCAG 2.2 AA (DESIGN.md §3.4, NFR-1.4)", () => {
  it("every approved body-text pairing meets >= 4.5:1", () => {
    for (const { text, background } of bodyTextOnBackground) {
      expect(contrastRatio(text, background)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("Plum Ink on Parchment is the default high-contrast body pairing", () => {
    expect(contrastRatio(color.purple900, color.cream50)).toBeGreaterThanOrEqual(4.5);
  });

  it("rejects Royal Gold body text on Parchment (it fails contrast)", () => {
    expect(contrastRatio(color.gold500, color.cream50)).toBeLessThan(4.5);
    const goldOnCream = bodyTextOnBackground.some(
      (p) => p.text === color.gold500 && p.background === color.cream50,
    );
    expect(goldOnCream).toBe(false);
  });
});
