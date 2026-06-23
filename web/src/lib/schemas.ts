/**
 * Zod validation layer (issue 067, FE-1.2, FR-1.4).
 *
 * Form input is parsed BEFORE any request is sent; API responses are parsed BEFORE use. Bounds
 * mirror the server schemas (api validation.py). Schemas are `.strict()` so unknown/extra fields
 * are rejected (no pass-through). Reject over sanitize — never truncate or coerce.
 */
import { z } from "zod";

// Anchored, bounded patterns mirroring the server (ReDoS-safe; length capped by .max()).
const EMAIL = z.string().max(254).regex(/^[^@\s]{1,64}@[^@\s.]{1,63}(?:\.[^@\s.]{1,63}){1,8}$/);
const PHONE = z.string().max(16).regex(/^\+?[0-9]{7,15}$/);

export const contactFormSchema = z
  .object({
    display_name: z.string().min(1).max(120),
    category_id: z.string().min(1).max(64),
    email: EMAIL.optional(),
    phone: PHONE.optional(),
    notes: z.string().max(2000).optional(),
  })
  .strict(); // reject unknown fields incl. owner_id / consent (no mass-assignment)

export type ContactForm = z.infer<typeof contactFormSchema>;

export const contactResponseSchema = z
  .object({
    id: z.string(),
    owner_id: z.string(),
    display_name: z.string(),
    category_id: z.string(),
    email: z.string().nullable().optional(),
    phone: z.string().nullable().optional(),
    notes: z.string().nullable().optional(),
  })
  .strict();

export const reminderResponseSchema = z
  .object({
    id: z.string(),
    contact_id: z.string(),
    channel: z.string(),
    status: z.string(),
    display_name: z.string().optional(),
    outreach_action: z.string().optional(),
  })
  .strict();

/** Parse a value, returning field-level errors instead of throwing (for inline display). */
export function safeValidate<T>(
  schema: z.ZodSchema<T>,
  value: unknown,
): { ok: true; data: T } | { ok: false; errors: Record<string, string> } {
  const result = schema.safeParse(value);
  if (result.success) return { ok: true, data: result.data };
  const errors: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const key = issue.path.join(".") || "_form";
    if (!(key in errors)) errors[key] = issue.message;
  }
  return { ok: false, errors };
}
