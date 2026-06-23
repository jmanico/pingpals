/**
 * API client: cookie session + CSRF header + AbortController fetch (issue 068, SEC-1.2, FE-1.7).
 *
 * The session is a server-set HttpOnly cookie sent automatically with `credentials: "include"` —
 * it is NEVER read or written by JS, never in localStorage/sessionStorage (SEC-1.2/INT-1.6). Every
 * mutating request attaches the double-submit anti-CSRF token (read from the non-HttpOnly csrf
 * cookie) as the `X-CSRF-Token` header (issue 026). Responses are validated through Zod before use
 * (issue 067); a failed response fails closed. `useFetch` aborts in-flight requests on unmount /
 * input change and discards stale results.
 */
import { useEffect, useState } from "react";
import type { z } from "zod";

const CSRF_COOKIE = "csrf_token";
const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {}

function readCsrfToken(): string | null {
  // The CSRF token is intentionally a readable cookie (double-submit). The SESSION cookie is
  // HttpOnly and is never accessible here.
  const match = document.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export async function apiFetch<T>(
  path: string,
  schema: z.ZodSchema<T>,
  options: RequestInit = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (MUTATING.has(method)) {
    const token = readCsrfToken();
    if (!token) throw new ApiError("missing CSRF token"); // fail closed before sending
    headers.set("X-CSRF-Token", token);
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...options, method, headers, credentials: "include" });
  if (!response.ok) throw new ApiError(`request failed: ${response.status}`);

  const body: unknown = await response.json();
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw new ApiError("response failed validation"); // AC-04 fail closed
  return parsed.data;
}

/** Race-safe data fetching: aborts on unmount/input change, discards stale resolutions. */
export function useFetch<T>(path: string, schema: z.ZodSchema<T>) {
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({
    loading: true,
  });

  useEffect(() => {
    const controller = new AbortController();
    let active = true; // ignore-flag guards against a stale resolution overwriting fresh data
    setState({ loading: true });
    apiFetch(path, schema, { signal: controller.signal })
      .then((data) => {
        if (active) setState({ data, loading: false });
      })
      .catch(() => {
        if (active && !controller.signal.aborted) {
          setState({ error: "Something went wrong. Please try again.", loading: false });
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [path, schema]);

  return state;
}
