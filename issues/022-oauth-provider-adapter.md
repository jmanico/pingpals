# Requirement: Generic OAuth provider adapter (PKCE, pinned least-privilege scopes, refresh rotation, encrypted tokens)

## Metadata
- **ID**: REQ-AUTH-022
- **Title**: Reusable Authorization Code + PKCE provider adapter with declared least-privilege scopes, refresh-token rotation/replay detection, and partitioned encrypted token storage
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The system MUST provide a generic OAuth provider adapter implementing the Authorization Code flow with PKCE (`S256`) for all integration providers. Each adapter MUST declare a pinned least-privilege scope set; the authorization request MUST be built from that declaration and verified against it at request time, and a flow requesting any scope outside the adapter's declared set MUST fail closed and MUST NOT proceed. Access tokens MUST be short-lived. Refresh tokens MUST be rotated on use with replay detection that revokes the whole token family on reuse. Tokens MUST NOT appear in URLs, logs, browser history, or any client-side storage. Tokens MUST be encrypted at rest with per-adapter, partitioned decrypt authority (issue 011 — an adapter can decrypt only its own provider's tokens). Each integration MUST be independently revocable by the user. Any broadening of an existing integration's authority (for example read to write/send), including via incremental or re-consent authorization, MUST require a new explicit, recorded user consent capturing the new scope (`PRIV-1.2`); absent that consent the broadened request MUST be denied.
- **Rationale**: A single hardened adapter centralizes the RFC 9700 controls for every provider (Google People in MVP; Microsoft Graph, calendar, messaging later), so least-privilege scoping, short-lived access tokens, refresh rotation with family revocation on replay, and token confidentiality are enforced once and consistently. Pinned scopes plus consent-gated broadening prevent silent scope creep into write/send authority.
- **Design**: Backend integration-adapter concern; the connect/disconnect and consent UI follow `DESIGN.md` §7. No tokens ever reach the client or any link.

## Scope
- **Applies To**: Both
- **Components**: Integration adapters (generic OAuth adapter + per-provider scope declarations); AuthN/Session subsystem (shared PKCE/`state`/`nonce` initiation via issue 017); persistence + KMS (encrypted token store, issue 011); Privacy/DSR (consent records for scope changes).
- **Actors**: Authenticated user connecting/disconnecting an integration; the external provider.
- **Data Classification**: Restricted (OAuth access/refresh tokens, provider credentials); Confidential (transaction state).

## Security Context
- **Defense Layer**: Architecture (single hardened OAuth path) + Strict API + Encryption-at-rest
- **Threat(s) Addressed**: Over-broad scope grants / scope creep (CWE-272 least-privilege violation), refresh-token theft/replay (CWE-294/CWE-384), token leakage via URLs/logs/storage (CWE-522/CWE-532), cross-adapter token decryption, unauthorized authority broadening. STRIDE: Elevation of Privilege, Information Disclosure, Spoofing.
- **Trust Boundary**: Trust boundary with each external provider; the token store sits behind the KMS/persistence boundary.
- **Zero Trust Consideration**: Each adapter holds only its own pinned scopes and only its own decrypt authority; the requested scope set is re-verified against the declaration at request time, and provider responses are validated before use (`SEC-4.1`).

## Standards Alignment
- **OWASP ASVS**: V51/V52 (OAuth — PKCE, scopes, token handling), V6 (cryptographic storage of tokens)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: AC-3, AC-6 (least privilege), IA-5, SC-12/SC-28 (key/encryption at rest)
- **NIST SP 800-207**: per-adapter least privilege; partitioned decrypt authority; no application-wide token role
- **Regulatory**: GDPR Art. 25 (data protection by design/default — minimum scopes), Art. 32; `PRIV-1.2` consent on scope change
- **Other**: RFC 9700, RFC 6749, RFC 7636 (PKCE); `INT-1.1`–`INT-1.7`, `SEC-3.1`, `SEC-3.3`, `SEC-5.2`, SECURITY §2/§5

## Acceptance Criteria
1. **AC-01**: Given an adapter with a declared pinned scope set, when an authorization request is built, then it requests exactly those scopes via Authorization Code + PKCE (`S256`); given a flow requesting any scope outside the declared set, then it fails closed and does not proceed.
2. **AC-02**: Given a refresh token is used, when it is exchanged, then it is rotated and the prior refresh token is invalidated; given a previously-used (replayed) refresh token, then the entire token family is revoked.
3. **AC-03**: Given any issued token, when it is stored or handled, then it is encrypted at rest under per-adapter partitioned decrypt authority (issue 011) and never appears in URLs, logs, browser history, or client-side storage.
4. **AC-04**: Given a user disconnects an integration, when revocation runs, then that integration's tokens are revoked and purged independently of any other adapter, and revoking one cannot affect another (`INT-1.7`).
5. **AC-05 (negative)**: Given an attempt to broaden an integration's authority (e.g. read→write/send) without a new recorded consent capturing the new scope, when processed, then the broadened request is denied. *(per `PRIV-1.2`, SECURITY §2.)*

## Failure Behavior
- **On Invalid Input**: Reject an out-of-declaration scope request or an unvalidated provider response (`SEC-4.1`) with a fail-closed error, write an audit entry (`SEC-8.1`), and disclose no token material.
- **On System Error**: Fail closed — if the token cannot be encrypted/stored, if the KMS decrypt is denied, or if replay state is indeterminate, deny the operation; never store or use a plaintext or unverified token.
- **Alerting**: Alert on refresh-token replay detections (family revocation) and on out-of-declaration scope-request attempts.

## Test Strategy
- **Unit Tests**: Scope-declaration enforcement (allow declared, reject out-of-set); PKCE request construction; refresh rotation and family-revocation-on-replay state machine; consent-gated broadening; token never serialized into logs/URLs.
- **Integration Tests**: End-to-end connect with Google People (least scope); refresh exchange rotates; replayed refresh revokes family; disconnect purges only that adapter's tokens; encrypted-at-rest round-trip via the KMS interface (issue 011).
- **Security Tests**: Attempt over-broad scope; replay an old refresh token; attempt cross-adapter decrypt (denied — maps to issue 011 partitioned-decrypt tests); grep build/logs for token leakage (maps to TEST-1.3 token non-exposure `INT-1.6`).
- **Compliance Tests**: Assert integration-token-use and scope-change-consent events are audit-logged (`SEC-8.1`, `PRIV-1.2`).
- **Coverage Target**: ≥ 80% branch coverage of the adapter and refresh-rotation modules.

## Dependencies
- **Upstream**: 017 (shared PKCE/`state`/`nonce` initiation + bounded transaction store), 011 (partitioned encrypted token storage / decrypt authority), consent-record subsystem (`PRIV-1.2`).
- **Downstream**: Google People contacts-import adapter and transactional-email adapter; later Microsoft Graph, calendar, messaging adapters; 023 (account/identity linking re-auth).
- **External**: Each OAuth provider's token + revocation endpoints; managed KMS (`TO BE DECIDED` — behind the key-store interface, default deny; raise a DECISION issue).

## Implementation Notes
- **Constraints**: One generic adapter; per-provider config = pinned scopes + endpoints + redirect URI (exact-match, issue 017). Refresh rotation with replay detection and family revocation is its own concern. Tokens encrypted with AES-256-GCM (or equivalent authenticated cipher) under managed keys; app code holds no raw key material. KMS vendor `TO BE DECIDED` — express behind the key-store interface, default to deny.
- **Anti-Patterns**: MUST NOT request scopes beyond the declaration; MUST NOT skip refresh rotation or family revocation; MUST NOT place tokens in URLs/logs/browser history/client storage; MUST NOT use a single application-wide decrypt role (issue 011); MUST NOT broaden authority without a new recorded consent; MUST NOT trust provider responses without schema validation (`SEC-4.1`).
- **Split recommendation:** if the adapter exceeds ~1500 LOC, extract the refresh-token rotation / replay-detection / family-revocation logic into a separate module consumed by the adapter.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Refresh-rotation/replay-detection and per-adapter scope/decrypt partitioning are intricate, high-blast-radius security logic; use the model with the strongest adversarial reasoning on OAuth token lifecycles. Mandatory human security review before merge.
