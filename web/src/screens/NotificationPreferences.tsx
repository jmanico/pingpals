/**
 * Notification preferences UI (issue 073, FR-7.x).
 *
 * Sets a preferred channel order and a global pause. A preference never authorizes delivery — the
 * server still gates on consent (FR-6.2); this UI only expresses preference and pause.
 */
import { Button, Card } from "../components";

export const CHANNELS = ["inapp", "email", "push", "sms", "whatsapp", "signal"] as const;
export type Channel = (typeof CHANNELS)[number];

export function GlobalPauseToggle(props: { paused: boolean; onToggle: (paused: boolean) => void }) {
  return (
    <Card ariaLabel="Pause all reminders">
      <label>
        <input
          type="checkbox"
          checked={props.paused}
          onChange={(e) => props.onToggle(e.target.checked)}
        />{" "}
        Pause all reminders
      </label>
      <p>{props.paused ? "Paused — the royal messenger rests." : "Active."}</p>
    </Card>
  );
}

export function ChannelOrder(props: {
  order: Channel[];
  onMoveUp: (channel: Channel) => void;
}) {
  return (
    <ul className="pp-list" aria-label="Preferred channel order">
      {props.order.map((channel, position) => (
        <li key={channel}>
          <span>
            {position + 1}. {channel}
          </span>
          <Button onClick={() => props.onMoveUp(channel)} disabled={position === 0}>
            Move up
          </Button>
        </li>
      ))}
    </ul>
  );
}
