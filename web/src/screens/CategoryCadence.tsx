/**
 * Category & cadence UI (issue 071, FR-2.x/3.x).
 *
 * Cadence is a positive integer interval; a zero/negative value is rejected inline. Deleting a
 * category requires choosing a reassignment target (the control disables delete until one is set).
 */
import { useState } from "react";

import { Button, Card, FormField } from "../components";

export interface Category {
  id: string;
  name: string;
  default_cadence_days: number;
}

export function CadenceField(props: {
  value: string;
  onChange: (v: string) => void;
  error?: string;
}) {
  return (
    <FormField
      id="cadence"
      label="Cadence (days)"
      value={props.value}
      onChange={props.onChange}
      error={props.error}
      type="number"
    />
  );
}

export function validateCadence(raw: string): { ok: true; days: number } | { ok: false; error: string } {
  const n = Number(raw);
  if (!Number.isInteger(n) || n < 1) {
    return { ok: false, error: "Enter a whole number of days, 1 or more." };
  }
  return { ok: true, days: n };
}

export function CategoryDeleteControl(props: {
  category: Category;
  others: Category[];
  onDelete: (reassignTo: string) => void;
}) {
  const [reassignTo, setReassignTo] = useState("");
  return (
    <Card ariaLabel={`Delete ${props.category.name}`}>
      <label htmlFor="reassign">Reassign contacts to</label>
      <select
        id="reassign"
        value={reassignTo}
        onChange={(e) => setReassignTo(e.target.value)}
      >
        <option value="">Choose a category…</option>
        {props.others.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <Button disabled={!reassignTo} onClick={() => props.onDelete(reassignTo)}>
        Delete category
      </Button>
    </Card>
  );
}
