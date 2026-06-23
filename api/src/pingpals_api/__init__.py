"""Pingpals Flask/REST API package.

Realizes the *logical* server components of ARCHITECTURE.md as source sub-packages. This is the
single trust boundary (ARCHITECTURE.md): every inbound edge validates and rejects untrusted input,
authorizes per request, and scopes all data access to the owning user (SEC-2.x).

No `TO BE DECIDED` infrastructure choice is committed in source: database engine, queue/broker,
KMS vendor, push provider, and cloud are kept behind interfaces that default to the most
restrictive (fail-closed) option until their DECISION issue is resolved (ARCHITECTURE.md).

Sub-packages (ARCHITECTURE.md → REQUIREMENTS.md tags):
    auth          AuthN/Session — OIDC SSO + WebAuthn/passkey + MFA, OAuth (SEC-1.x, INT-1.x)
    scheduler     Cadence evaluation + idempotent reminder generation (FR-5.x, NFR-1.1)
    delivery      Per-channel reminder delivery worker, fail-closed consent (FR-6.x, INT-5.x)
    outreach      Deep-link builder behind an allowlist validator (FR-6.4, SEC-4.3)
    integrations  Least-privilege OAuth/scoped contact, calendar, mailbox, messaging adapters
    privacy       Consent records, export, erasure cascade, retention, DSR (PRIV-1.x)
    persistence   Per-user repository layer + KMS/crypto substrate (SEC-2.2, SEC-3.x, SEC-5.x)
    audit         Tamper-evident append-only / hash-chained audit log (SEC-8.x)
"""

__version__ = "0.1.0"
