/**
 * Contact management UI (issue 070, FR-1.x, FE-1.2).
 *
 * Create form is Zod-validated BEFORE any request (inline field-level errors, no request on
 * failure); the contact list keys on the stable contact id. No prop spreading, no inline styles.
 */
import { useState } from "react";

import { Button, Card, FormField } from "../components";
import { contactFormSchema, safeValidate } from "../lib/schemas";

export interface Contact {
  id: string;
  display_name: string;
  email?: string | null;
}

export function ContactForm(props: {
  categoryId: string;
  onSubmit: (data: { display_name: string; category_id: string; email?: string }) => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  function handleSubmit() {
    const candidate: Record<string, unknown> = {
      display_name: displayName,
      category_id: props.categoryId,
    };
    if (email) candidate.email = email;
    const result = safeValidate(contactFormSchema, candidate);
    if (!result.ok) {
      setErrors(result.errors); // inline errors; NO request is sent (AC reject-over-sanitize)
      return;
    }
    setErrors({});
    props.onSubmit(result.data);
  }

  return (
    <Card ariaLabel="Add a pal to your court">
      <FormField
        id="display_name"
        label="Display name"
        value={displayName}
        onChange={setDisplayName}
        error={errors.display_name}
      />
      <FormField
        id="email"
        label="Email (optional)"
        value={email}
        onChange={setEmail}
        error={errors.email}
        type="email"
      />
      <Button type="button" onClick={handleSubmit}>
        Add pal
      </Button>
    </Card>
  );
}

export function ContactList(props: { contacts: Contact[]; onDelete: (id: string) => void }) {
  return (
    <ul className="pp-list">
      {props.contacts.map((c) => (
        <li key={c.id}>
          <Card ariaLabel={c.display_name}>
            <span>{c.display_name}</span>
            <Button variant="primary" onClick={() => props.onDelete(c.id)}>
              Remove
            </Button>
          </Card>
        </li>
      ))}
    </ul>
  );
}
