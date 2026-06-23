/** Zod validation layer tests (issue 067 / REQ-FRONTEND-056, FE-1.2, FR-1.4). */
import { describe, expect, it } from "vitest";

import { contactFormSchema, contactResponseSchema, safeValidate } from "./schemas";

describe("contact form schema", () => {
  it("accepts a valid contact (AC-01)", () => {
    const r = safeValidate(contactFormSchema, {
      display_name: "Alex",
      category_id: "cat1",
      email: "alex@example.com",
    });
    expect(r.ok).toBe(true);
  });

  it("rejects invalid email/phone with field-level errors (AC-01)", () => {
    const r = safeValidate(contactFormSchema, {
      display_name: "Alex",
      category_id: "cat1",
      email: "bad@@x",
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.email).toBeTruthy();
  });

  it("rejects unknown / consent fields (no mass-assignment, AC-02-form)", () => {
    const r = safeValidate(contactFormSchema, {
      display_name: "Alex",
      category_id: "cat1",
      consent_email: true,
    });
    expect(r.ok).toBe(false);
  });

  it("rejects over-length, never truncates (AC-04)", () => {
    const r = safeValidate(contactFormSchema, {
      display_name: "A".repeat(200),
      category_id: "cat1",
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.display_name).toBeTruthy();
  });
});

describe("response schema", () => {
  it("rejects responses with extra fields (AC-02)", () => {
    const r = safeValidate(contactResponseSchema, {
      id: "c1",
      owner_id: "alice",
      display_name: "Alex",
      category_id: "cat1",
      injected: "evil",
    });
    expect(r.ok).toBe(false);
  });
});
