# Requirement: Authentication UI (Google SSO, WebAuthn passkey, MFA step-up)

## Metadata
- **ID**: REQ-FE-058
- **Title**: Authentication UI — Google SSO sign-in, passkey registration/assertion, MFA step-up (no password-only path)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The frontend MUST provide the authentication UI for: (a) initiating Google OIDC SSO sign-in, (b) registering a WebAuthn passkey and performing a passkey assertion via `navigator.credentials`, and (c) prompting MFA step-up. A password-only authentication path MUST NOT exist or be presented anywhere in the UI. All ceremony state (challenges, options) MUST come from the server and MUST NOT be fabricated client-side; the client only relays browser-credential results to the server for verification. Authentication errors MUST be gentle and non-blaming (DESIGN §6) but MUST NOT soften a validation failure into ambiguity, and MUST NOT leak whether an account exists or why a server check failed.
- **Rationale**: The UI surfaces the auth model fixed in SECURITY §2 and `SEC-1.x`/`INT-1.x`: OIDC (Google) SSO + WebAuthn/passkeys with MFA, no password-only path. The browser ceremony for passkeys (`navigator.credentials.create`/`.get`) is inherently client-side; this issue builds those affordances while keeping all verification server-side (issues 017–021).
- **Design**: Per `DESIGN.md` §7, the sign-in surface is a Parchment-background card with the primary lockup (mascot + wordmark + tagline, DESIGN §2.1) and a Royal Purple (`--color-purple-700`) primary action; the passkey prompt and MFA step-up reuse the speech-bubble/crown motifs (DESIGN §5) for a regal-but-reassuring tone (DESIGN §1, §6). Errors use DESIGN §6 voice ("That didn't go through…") and token-driven `--color-danger`. Focus uses the Gilt ring (DESIGN §7); all states meet WCAG 2.2 AA (`NFR-1.4`).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — sign-in screen, passkey registration/assertion components (`navigator.credentials`), MFA step-up prompt; consumes the API client (057) for all server exchanges.
- **Actors**: Unauthenticated visitor initiating sign-in; authenticated user registering a passkey or completing step-up.
- **Data Classification**: Confidential (session material, ceremony challenges); the UI holds none of it persistently and never in script-accessible storage.

## Security Context
- **Defense Layer**: Authentication (UI relay of phishing-resistant ceremonies; all verification server-side).
- **Threat(s) Addressed**: Phishing/credential theft (mitigated by passkeys, CWE-287/OWASP A07:2021), account enumeration via differential errors (CWE-204), client-fabricated challenge replay, password-based attacks (eliminated by no-password design). STRIDE: Spoofing, Information Disclosure.
- **Trust Boundary**: Client-server edge. The client performs the browser credential ceremony but makes no authentication decision; the server verifies the OIDC ID token (018), WebAuthn registration (020) and assertion/MFA (021), issues the session, and the UI only reflects success/failure.
- **Zero Trust Consideration**: The UI never trusts its own state to assert "authenticated"; authentication is true only when the server returns a session. Challenges are server-generated, single-use, and bound server-side (`INT-1.8`, SECURITY §2 WebAuthn rules); the client just relays them.

## Standards Alignment
- **OWASP ASVS**: V2 (authentication), V2.2 (general authenticator), V3 (session)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: IA-2 (identification & authentication), IA-8, AC-7
- **NIST SP 800-207**: authentication decision server-side per request
- **Regulatory**: n/a
- **Other**: FIDO2/WebAuthn, RFC 9700, RFC 9068, OIDC Core; `SEC-1.1`, `SEC-1.2`, `INT-1.1`, `INT-1.8`, `INT-1.9`

## Acceptance Criteria
1. **AC-01**: Given the sign-in screen, when rendered, then it offers Google SSO and passkey/MFA only, with no password field or password-only path anywhere. *(verbatim `SEC-1.1`: a password-only path MUST NOT exist.)*
2. **AC-02**: Given a user starts passkey registration in an authenticated session, when the ceremony runs, then the client calls `navigator.credentials.create` with server-provided options and relays the result to the server for verification (020); the client fabricates no challenge.
3. **AC-03**: Given a passkey assertion or MFA step-up, when performed, then the client calls `navigator.credentials.get` with the server-issued challenge and the session is granted only after the server verifies it (021); a failed verification yields no session.
4. **AC-04 (negative)**: Given a failed login (bad SSO callback, failed assertion, or unknown account), when surfaced, then the error is gentle and uniform — it MUST NOT reveal whether an account exists, which factor failed in an exploitable way, or any internal detail.
5. **AC-05 (negative)**: Given any auth screen, when inspected, then no session identifier or token is written to script-accessible storage (defers to 057) and no client-side flag alone is treated as "authenticated".
6. **AC-06 (accessibility)**: Given each auth state (loading, error, step-up), when rendered, then it meets WCAG 2.2 AA — visible Gilt focus ring never removed, status conveyed by text/icon not color alone, contrast ≥ 4.5:1 body (`NFR-1.4`, DESIGN §3.4).

## Failure Behavior
- **On Invalid Input**: A failed ceremony or callback shows a gentle, uniform error; no session is established; the client re-fetches a fresh challenge from the server rather than reusing one.
- **On System Error**: Fail closed — any server/ceremony error denies the session; the UI never grants access on a client-side assumption (`SEC-2.3`, `INT-1.8`).
- **Alerting**: Repeated failed assertions/step-ups MAY feed the server's auth-event monitoring (`SEC-8.1`); the client emits no PII.

## Test Strategy
- **Unit Tests**: Render asserts no password path; ceremony components call `navigator.credentials.*` with server options and never self-generate challenges; error renderer produces uniform non-enumerating messages.
- **Integration Tests**: SSO initiation → callback → session (with 017/018); passkey register then assert (with 020/021); MFA step-up gate; failed verification yields no session.
- **Security Tests**: Confirm no enumeration via error differences; confirm no token in script storage; replayed/stale challenge is rejected by the server and the UI reflects denial (maps to SEC-1.x/INT-1.x tests).
- **Compliance Tests**: Evidence that the only auth paths presented are SSO + passkey/MFA (no password).
- **Coverage Target**: ≥ 80% branch coverage of auth UI components and ceremony relay logic.

## Dependencies
- **Upstream**: 054 (scaffold), 057 (API client), 017 (OIDC SSO initiation), 018 (ID-token validation), 019 (session), 020 (WebAuthn registration), 021 (WebAuthn assertion/MFA), 064 (component library), 005 (tokens).
- **Downstream**: 059–063 (all authenticated UIs require a session established here), 023 (account linking re-auth UI may reuse step-up).
- **External**: Google as OIDC IdP; the browser WebAuthn (`navigator.credentials`) API.

## Implementation Notes
- **Constraints**: Browser-only ceremony relay; all verification is server-side (018/020/021). No password UI, ever. Challenges/options are server-issued, single-use, never cached or reused client-side. **Split recommendation**: if the combined UI exceeds ~1500 LOC, split into (a) Google SSO sign-in flow and (b) passkey registration + assertion/MFA step-up flow as separate issues sharing the API client.
- **Anti-Patterns**: MUST NOT present a password-only path (`SEC-1.1`); MUST NOT fabricate or reuse WebAuthn challenges client-side (SECURITY §2); MUST NOT store session material in script-accessible storage (`SEC-1.2`, via 057); MUST NOT emit account-enumerating or detail-leaking errors; MUST NOT treat a client flag as proof of authentication (ARCH Rule 1).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Ceremony relay against a fixed WebAuthn/OIDC contract is well-documented, pattern-driven UI work suited to broad, consistent generation. Mandatory human security review of the no-enumeration error handling and the "no client-side authn decision" invariant before merge.
