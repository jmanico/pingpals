/** Base component + secure-render guard tests (issues 065/075). */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button, FormField, SafeLink, StatusBadge } from "./index";

// All source modules' raw text, loaded at build time by Vite (no node fs needed).
const SOURCES = import.meta.glob("../**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

describe("base components", () => {
  it("Button renders explicit children and fires onClick", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Send word</Button>);
    const btn = screen.getByRole("button", { name: "Send word" });
    btn.click();
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("FormField associates its error with the input (AC-05/AC-07)", () => {
    render(
      <FormField id="email" label="Email" value="bad" onChange={() => {}} error="Invalid email" />,
    );
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-describedby", "email-error");
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid email");
  });

  it("StatusBadge conveys status by icon + label, not colour alone (AC-04)", () => {
    render(<StatusBadge status="danger" label="Overdue" />);
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("SafeLink sanitizes a javascript: href to '#'", () => {
    render(<SafeLink href="javascript:alert(1)">Open</SafeLink>);
    expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute("href", "#");
  });

  it("SafeLink passes a valid mailto through", () => {
    render(<SafeLink href="mailto:a@example.com">Email</SafeLink>);
    expect(screen.getByRole("link", { name: "Email" })).toHaveAttribute("href", "mailto:a@example.com");
  });
});

// Secure-render invariants enforced as a build gate (issue 065 AC-03/AC-05, FE-1.1/1.6).
describe("secure-render source guard", () => {
  const sourceFiles = Object.entries(SOURCES).filter(
    ([path]) => !path.includes(".test."),
  );

  it("no source uses dangerouslySetInnerHTML (FE-1.1)", () => {
    // Match actual JSX usage (prop assignment), not a mention in a comment.
    for (const [, text] of sourceFiles) {
      expect(text).not.toMatch(/dangerouslySetInnerHTML\s*[=:]/);
    }
  });

  it("no source uses an array index as a React key (FE-1.6)", () => {
    for (const [, text] of sourceFiles) {
      expect(text).not.toMatch(/key=\{\s*(?:index|i|idx)\s*\}/);
    }
  });
});
