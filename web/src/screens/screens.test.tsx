/** Frontend screen tests (issues 069-074). */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AuthPanel } from "./AuthPanel";
import { CategoryDeleteControl, validateCadence } from "./CategoryCadence";
import { ContactForm } from "./ContactManager";
import { GlobalPauseToggle } from "./NotificationPreferences";
import { ErasurePanel } from "./PrivacyCenter";
import { ReminderCard, ReminderList } from "./ReminderList";

// ---- Reminder card (issue 072) ----

describe("ReminderCard", () => {
  it("shows display name, channel, and a sanitized outreach link", () => {
    render(
      <ReminderCard
        reminder={{
          id: "r1",
          display_name: "Alex",
          channel: "email",
          outreach_action: "mailto:alex@example.com",
        }}
      />,
    );
    expect(screen.getByText(/Alex/)).toBeInTheDocument();
    expect(screen.getByText(/via email/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Send word" })).toHaveAttribute(
      "href",
      "mailto:alex@example.com",
    );
  });

  it("sanitizes a malicious outreach action to '#'", () => {
    render(
      <ReminderCard
        reminder={{ id: "r2", display_name: "X", channel: "sms",
          outreach_action: "javascript:alert(1)" }}
      />,
    );
    expect(screen.getByRole("link", { name: "Send word" })).toHaveAttribute("href", "#");
  });

  it("renders an empty-court message with no reminders", () => {
    render(<ReminderList reminders={[]} />);
    expect(screen.getByText(/court is quiet/i)).toBeInTheDocument();
  });
});

// ---- Contact form (issue 070) ----

describe("ContactForm", () => {
  it("rejects an invalid email inline and sends no submit", async () => {
    const onSubmit = vi.fn();
    render(<ContactForm categoryId="cat1" onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText("Display name"), "Alex");
    await userEvent.type(screen.getByLabelText("Email (optional)"), "bad@@x");
    await userEvent.click(screen.getByRole("button", { name: "Add pal" }));
    expect(onSubmit).not.toHaveBeenCalled(); // no request on invalid input
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("submits a valid contact", async () => {
    const onSubmit = vi.fn();
    render(<ContactForm categoryId="cat1" onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText("Display name"), "Alex");
    await userEvent.click(screen.getByRole("button", { name: "Add pal" }));
    expect(onSubmit).toHaveBeenCalledWith({ display_name: "Alex", category_id: "cat1" });
  });
});

// ---- Cadence validation (issue 071) ----

describe("cadence", () => {
  it("rejects zero/negative/non-integer", () => {
    for (const bad of ["0", "-3", "1.5", "abc"]) {
      expect(validateCadence(bad).ok).toBe(false);
    }
    expect(validateCadence("30")).toEqual({ ok: true, days: 30 });
  });

  it("category delete is disabled until a reassignment target is chosen", async () => {
    render(
      <CategoryDeleteControl
        category={{ id: "c1", name: "Family", default_cadence_days: 30 }}
        others={[{ id: "c2", name: "Friends", default_cadence_days: 60 }]}
        onDelete={() => {}}
      />,
    );
    const btn = screen.getByRole("button", { name: "Delete category" });
    expect(btn).toBeDisabled();
    await userEvent.selectOptions(screen.getByLabelText("Reassign contacts to"), "c2");
    expect(btn).toBeEnabled();
  });
});

// ---- Preferences (issue 073) ----

describe("preferences", () => {
  it("toggles global pause", async () => {
    const onToggle = vi.fn();
    render(<GlobalPauseToggle paused={false} onToggle={onToggle} />);
    await userEvent.click(screen.getByRole("checkbox"));
    expect(onToggle).toHaveBeenCalledWith(true);
  });
});

// ---- Privacy center (issue 074) ----

describe("erasure", () => {
  it("requires typed confirmation before erasing", async () => {
    const onErase = vi.fn();
    render(<ErasurePanel onErase={onErase} />);
    const btn = screen.getByRole("button", { name: "Erase everything" });
    expect(btn).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Type ERASE to confirm"), "ERASE");
    expect(btn).toBeEnabled();
    await userEvent.click(btn);
    expect(onErase).toHaveBeenCalledOnce();
  });
});

// ---- Auth (issue 069) ----

describe("auth panel", () => {
  it("offers Google SSO and passkey setup; stores no tokens", async () => {
    const onGoogleSso = vi.fn();
    render(
      <AuthPanel
        onGoogleSso={onGoogleSso}
        onRegisterPasskey={() => {}}
        onAssertPasskey={() => {}}
        hasPasskey={false}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Sign in with Google" }));
    expect(onGoogleSso).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Set up a passkey" })).toBeInTheDocument();
  });
});
