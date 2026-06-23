/**
 * Reminder list + reminder card (issue 072, FR-5.4, DESIGN §7).
 *
 * Each card shows ONLY the minimal payload — contact display name, chosen channel, and a single
 * one-tap outreach action (a speech-bubble motif). The outreach link passes the allowlist validator
 * and renders `"#"` if invalid. Keys are stable domain ids, never the array index (FE-1.6).
 */
import { Card, SafeLink, StatusBadge } from "../components";

export interface Reminder {
  id: string;
  display_name: string;
  channel: string;
  outreach_action: string;
  status?: "success" | "warning" | "danger";
}

export function ReminderCard(props: { reminder: Reminder }) {
  const r = props.reminder;
  return (
    <Card ariaLabel={`Reminder for ${r.display_name}`}>
      <p>💬 Your Majesty, it&apos;s been a while since you pinged {r.display_name}.</p>
      <StatusBadge status={r.status ?? "warning"} label={`via ${r.channel}`} />
      <p>
        <SafeLink href={r.outreach_action}>Send word</SafeLink>
      </p>
    </Card>
  );
}

export function ReminderList(props: { reminders: Reminder[] }) {
  if (props.reminders.length === 0) {
    return <p>The court is quiet. Add your first pal to begin your reign.</p>;
  }
  return (
    <ul className="pp-list">
      {props.reminders.map((reminder) => (
        <li key={reminder.id}>
          <ReminderCard reminder={reminder} />
        </li>
      ))}
    </ul>
  );
}
