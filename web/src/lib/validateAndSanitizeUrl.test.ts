/** validateAndSanitizeUrl tests (issue 066 / REQ-FRONTEND-055, FR-6.4). */
import { describe, expect, it } from "vitest";

import { SAFE_FALLBACK, validateAndSanitizeUrl } from "./validateAndSanitizeUrl";

describe("validateAndSanitizeUrl", () => {
  it("returns allowed scheme URLs unchanged (AC-01)", () => {
    for (const url of [
      "mailto:alex@example.com",
      "tel:+15551234567",
      "sms:+15551234567",
      "https://wa.me/15551234567",
      "signal://send?phone=%2B15551234567",
    ]) {
      expect(validateAndSanitizeUrl(url)).toBe(url);
    }
  });

  it("rejects dangerous schemes to '#' (AC-03)", () => {
    for (const url of [
      "javascript:alert(1)",
      "data:text/html,<script>alert(1)</script>",
      "file:///etc/passwd",
      "vbscript:msgbox",
      "JAVASCRIPT:alert(1)",
    ]) {
      expect(validateAndSanitizeUrl(url)).toBe(SAFE_FALLBACK);
    }
  });

  it("rejects lookalike click-to-chat hosts (AC-02)", () => {
    expect(validateAndSanitizeUrl("https://wa.me/15551234567")).toBe("https://wa.me/15551234567");
    for (const url of [
      "https://wa.me.evil.example/1555",
      "https://evil.example/wa.me",
      "https://wa.me@evil.example/",
      "https://wa.me:8443/x",
      "https://api.whatsapp.example/1555",
    ]) {
      expect(validateAndSanitizeUrl(url)).toBe(SAFE_FALLBACK);
    }
  });

  it("rejects authority injection on authority-less schemes (AC-04)", () => {
    expect(validateAndSanitizeUrl("tel://evil.example")).toBe(SAFE_FALLBACK);
    expect(validateAndSanitizeUrl("mailto://evil.example")).toBe(SAFE_FALLBACK);
    expect(validateAndSanitizeUrl("sms://evil.example")).toBe(SAFE_FALLBACK);
  });

  it("handles empty / non-string input", () => {
    for (const v of ["", "   ", null, undefined, 42, {}]) {
      expect(validateAndSanitizeUrl(v)).toBe(SAFE_FALLBACK);
    }
  });
});
