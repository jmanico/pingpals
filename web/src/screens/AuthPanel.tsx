/**
 * Auth UI (issue 069, SEC-1.x, INT-1.x).
 *
 * Initiates the server-driven auth flows — Google SSO, passkey register/assert, MFA step-up — by
 * calling endpoints; the client makes NO authorization decision and never stores tokens. Buttons
 * trigger redirects/ceremonies the server validates.
 */
import { Button, Card } from "../components";

export function AuthPanel(props: {
  onGoogleSso: () => void;
  onRegisterPasskey: () => void;
  onAssertPasskey: () => void;
  hasPasskey: boolean;
}) {
  return (
    <Card ariaLabel="Sign in to Pingpals">
      <h1>Long live your reign</h1>
      <Button variant="primary" onClick={props.onGoogleSso}>
        Sign in with Google
      </Button>
      {props.hasPasskey ? (
        <Button onClick={props.onAssertPasskey}>Continue with passkey</Button>
      ) : (
        <Button onClick={props.onRegisterPasskey}>Set up a passkey</Button>
      )}
      <p>Authentication is verified by the server; this device stores no tokens.</p>
    </Card>
  );
}
