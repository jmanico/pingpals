/**
 * validateAndSanitizeUrl — client-side outreach/href allowlist (issue 066, FR-6.4, FE-1.3).
 *
 * Mirrors the server-side validator (api outreach/links.py). Every `href`/`src` and every outreach
 * deep link passes through this before reaching the DOM. Allowed schemes: mailto, tel, sms, https
 * (restricted to an EXACT-match click-to-chat host), and the Signal scheme. Anything else — a
 * lookalike host, an authority-injection, or a `javascript:`/`data:`/`file:` scheme — resolves to
 * the safe fallback `"#"`. Reject over sanitize.
 */

export const SAFE_FALLBACK = "#";
const CLICK_TO_CHAT_HOSTS = new Set(["wa.me"]);
const ALLOWED_SCHEMES = new Set(["mailto:", "tel:", "sms:", "https:", "signal:"]);

export function validateAndSanitizeUrl(raw: unknown): string {
  if (typeof raw !== "string" || raw.trim() === "") return SAFE_FALLBACK;

  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return SAFE_FALLBACK;
  }

  const scheme = url.protocol.toLowerCase();
  if (!ALLOWED_SCHEMES.has(scheme)) return SAFE_FALLBACK; // javascript:/data:/file: -> "#"

  if (scheme === "https:") {
    // Exact host match only; reject userinfo/port/lookalikes (AC-02/AC-04).
    if (url.username || url.password || url.port) return SAFE_FALLBACK;
    if (!CLICK_TO_CHAT_HOSTS.has(url.hostname)) return SAFE_FALLBACK; // wa.me.evil.example !== wa.me
    return raw;
  }

  if (scheme === "mailto:" || scheme === "tel:" || scheme === "sms:") {
    // These schemes carry no authority; an embedded "//" is an injection attempt (AC-04).
    if (raw.slice(scheme.length).startsWith("//")) return SAFE_FALLBACK;
  }
  return raw;
}
