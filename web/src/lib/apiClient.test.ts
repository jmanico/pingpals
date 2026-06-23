/** API client tests (issue 068 / REQ-FRONTEND-057, SEC-1.2, FE-1.7). */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { ApiError, apiFetch } from "./apiClient";

const schema = z.object({ ok: z.boolean() }).strict();

function mockResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: async () => body } as Response;
}

describe("apiFetch", () => {
  beforeEach(() => {
    document.cookie = "csrf_token=tok-abc123";
  });
  afterEach(() => {
    vi.restoreAllMocks();
    document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  it("attaches the CSRF header on mutating requests and uses credentials (AC-02)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await apiFetch("/contacts", schema, { method: "POST", body: "{}" });
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Headers).get("X-CSRF-Token")).toBe("tok-abc123");
    expect(init.credentials).toBe("include");
  });

  it("fails closed when no CSRF token is present (AC-02)", async () => {
    document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    vi.stubGlobal("fetch", vi.fn());
    await expect(apiFetch("/contacts", schema, { method: "POST" })).rejects.toBeInstanceOf(ApiError);
  });

  it("does not send a CSRF header on GET", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await apiFetch("/contacts", schema);
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Headers).get("X-CSRF-Token")).toBeNull();
  });

  it("validates the response and fails closed on schema mismatch (AC-04)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse({ ok: true, extra: "x" })));
    await expect(apiFetch("/contacts", schema)).rejects.toBeInstanceOf(ApiError);
  });

  it("throws on non-2xx", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse({}, false, 403)));
    await expect(apiFetch("/contacts", schema)).rejects.toBeInstanceOf(ApiError);
  });
});
