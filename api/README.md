# Pingpals API (Flask / REST)

The server module and single trust boundary (ARCHITECTURE.md): per-request authorization, strict
per-user tenant isolation, fail-closed by default. Realizes the logical components of
ARCHITECTURE.md as `src/pingpals_api/` sub-packages (`auth`, `scheduler`, `delivery`, `outreach`,
`integrations`, `privacy`, `persistence`, `audit`).

## Layout

```
api/
  pyproject.toml             # manifest; pinned, minimal deps (no TO BE DECIDED infra SDKs)
  requirements.lock.txt      # hash-pinned runtime deps (pip --require-hashes) — REQ-FND-004
  requirements-dev.lock.txt  # hash-pinned dev/CI tooling
  Dockerfile                 # hardened multi-stage, non-root, digest-pinned — REQ-FND-002
  src/pingpals_api/          # source (src layout)
  tests/                     # pytest suite (>=80% coverage gate)
```

## Dependency policy (REQ-FND-001 / SEC-9.1 / SEC-9.3)

Runtime deps are deliberately minimal and contain **no** library that resolves a `TO BE DECIDED`
infrastructure choice — no DB driver, queue/broker client, KMS vendor SDK, or cloud SDK. Those
stay behind interfaces (default-deny) until their DECISION issue is resolved.

To regenerate the locks after editing `requirements.in` / `requirements-dev.in`:

```bash
uv pip compile --generate-hashes --universal -o requirements.lock.txt requirements.in
uv pip compile --generate-hashes --universal -o requirements-dev.lock.txt requirements-dev.in
```

## Local checks

The merge-blocking gates live in `../scripts/ci-api.sh` (ruff, bandit, pip-audit, pytest+coverage).
Concrete build/run commands for the Flask app land with issue 018 (the app skeleton is a
placeholder here — REQ-FND-001 scope is layout only).
