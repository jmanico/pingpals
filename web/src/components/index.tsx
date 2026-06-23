/**
 * Base component library (issues 065/075, FE-1.1/1.5/1.6, DESIGN §3.4/§7).
 *
 * All visual values come from design tokens (no hard-coded hex/px). No `dangerouslySetInnerHTML`,
 * no prop spreading onto DOM nodes, list keys use stable ids / `crypto.randomUUID()`. Status is
 * conveyed by icon + label (not colour alone); every interactive element shows the Gilt focus ring.
 */
import type { ReactNode } from "react";

import { SAFE_FALLBACK, validateAndSanitizeUrl } from "../lib/validateAndSanitizeUrl";
import "./components.css";

export function Button(props: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "gold";
  type?: "button" | "submit";
  disabled?: boolean;
}) {
  const className = props.variant === "gold" ? "pp-button pp-button--gold" : "pp-button";
  // Explicit props only — never `{...props}` onto the DOM node (FE-1.5).
  return (
    <button
      className={className}
      onClick={props.onClick}
      type={props.type ?? "button"}
      disabled={props.disabled}
    >
      {props.children}
    </button>
  );
}

export function Card(props: { children: ReactNode; ariaLabel?: string }) {
  return (
    <section className="pp-card" aria-label={props.ariaLabel}>
      {props.children}
    </section>
  );
}

export function FormField(props: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  type?: string;
}) {
  const errorId = `${props.id}-error`;
  return (
    <div className="pp-field">
      <label htmlFor={props.id}>{props.label}</label>
      <input
        id={props.id}
        className="pp-input"
        type={props.type ?? "text"}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        aria-invalid={props.error ? true : undefined}
        aria-describedby={props.error ? errorId : undefined}
      />
      {props.error ? (
        // Error conveyed by TEXT (not colour alone), programmatically associated (AC-05/AC-07).
        <span id={errorId} className="pp-field__error" role="alert">
          {props.error}
        </span>
      ) : null}
    </div>
  );
}

const STATUS_ICON: Record<string, string> = {
  success: "✓",
  warning: "⏳",
  danger: "⚠",
};

export function StatusBadge(props: { status: "success" | "warning" | "danger"; label: string }) {
  return (
    <span className={`pp-status pp-status--${props.status}`}>
      <span aria-hidden="true">{STATUS_ICON[props.status]}</span>
      <span>{props.label}</span>
    </span>
  );
}

export function SafeLink(props: { href: string; children: ReactNode }) {
  // Every href passes the allowlist validator; invalid -> "#" (FE-1.3, FR-6.4).
  const href = validateAndSanitizeUrl(props.href);
  return (
    <a className="pp-link" href={href} rel="noopener noreferrer">
      {props.children}
    </a>
  );
}

export { SAFE_FALLBACK };
