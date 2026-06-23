"""API service entrypoint (placeholder).

The hardened Flask application factory — `debug=False` in all non-dev builds, strong SECRET_KEY
sourced from the secret store, strict CSP / security headers, narrow CORS allowlist, and
per-request authorization — is intentionally NOT implemented in REQ-FND-001 (scaffolding).

It is the subject of issue 018 ([BACKEND] Flask app skeleton + hardened config) and issue 019
([BACKEND] HTTP boundary). This module only reserves the entrypoint location so downstream
issues (and Docker, REQ-FND-002) have a stable target.

Anti-pattern guard (SECURITY.md §8): no debug server, no app object is constructed here, and no
SECRET_KEY is hard-coded.
"""
