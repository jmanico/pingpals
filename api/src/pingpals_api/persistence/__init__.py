"""Persistence + secret/key management (stub).

Per-user-scoped repository layer (every query carries the owning user as a non-optional
constraint — SEC-2.2, ARCH Rule 4) over PostgreSQL behind a repository interface (engine not
coupled to source). Restricted data is encrypted at rest with managed keys; application code holds
no raw key material. The crypto-agility substrate lives in `persistence.crypto` (REQ-FND-006).

The concrete PostgreSQL driver and managed-KMS vendor are NOT imported here — they are `TO BE
DECIDED` and stay behind the repository / key-store interfaces, defaulting to deny.
Tags: SEC-2.2, SEC-3.x, SEC-5.x. Implementation tracked in issues 010-011, 021-022.
"""
