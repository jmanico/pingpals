/**
 * Consent & privacy center UI (issue 074, PRIV-1.x).
 *
 * Surfaces the data-subject rights: per-channel consent toggles, machine-readable export download,
 * and account erasure behind an explicit confirmation. Erasure is irreversible, so the button is
 * gated on a typed confirmation. No tokens are stored client-side.
 */
import { useState } from "react";

import { Button, Card } from "../components";

export function ConsentToggle(props: {
  channel: string;
  granted: boolean;
  onChange: (channel: string, granted: boolean) => void;
}) {
  return (
    <label>
      <input
        type="checkbox"
        checked={props.granted}
        onChange={(e) => props.onChange(props.channel, e.target.checked)}
      />{" "}
      {props.channel}
    </label>
  );
}

export function ExportPanel(props: { onExport: () => void }) {
  return (
    <Card ariaLabel="Export your data">
      <p>Download a machine-readable copy of all data held for you.</p>
      <Button onClick={props.onExport}>Export my data</Button>
    </Card>
  );
}

export function ErasurePanel(props: { onErase: () => void }) {
  const [confirm, setConfirm] = useState("");
  const armed = confirm === "ERASE";
  return (
    <Card ariaLabel="Erase your account">
      <p>This permanently erases your account and all contact data. This cannot be undone.</p>
      <label htmlFor="erase-confirm">Type ERASE to confirm</label>
      <input
        id="erase-confirm"
        className="pp-input"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
      />
      <Button variant="primary" disabled={!armed} onClick={props.onErase}>
        Erase everything
      </Button>
    </Card>
  );
}
