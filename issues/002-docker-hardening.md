# Requirement: Hardened multi-stage Docker images for the API and SPA

## Metadata
- **ID**: REQ-FND-002
- **Title**: Non-root, minimal, secret-free multi-stage container images for the Flask API and React 19 SPA
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The repository MUST provide hardened, multi-stage Dockerfiles for the Flask API and the React 19 SPA build that: run the runtime process as a **non-root** user; use a **minimal, pinned (digest-pinned)** base image; install **no build toolchain into the runtime layer**; bake **no secrets** and accept **no secret build args**; and ship **no debug server** (no Werkzeug debugger, no dev server in the runtime image). The build stage and the runtime stage MUST be separated so that compilers, dev dependencies, and SPA build tooling never appear in the final runtime image.
- **Rationale**: Packaging is fixed as a cloud-portable Docker image (`ARCHITECTURE.md`). A container that runs as root, carries a build toolchain, embeds secrets, or exposes a debugger materially widens the attack surface and violates SECURITY §8 (Deployment & CI/CD safety) and `SEC-3.2` (no secrets in images/build args). Minimal pinned bases reduce CVE exposure (`SEC-9.1`) and make the image reproducible for SBOM/pinning (004).
- **Design**: No user-facing surface. The SPA runtime image serves the static client bundle (per `DESIGN.md` the bundle ships brand assets); the API image runs the Flask app with `debug=False`. Token/secret handling defers to SECURITY §5 — secrets are injected at runtime from the secret store (DECISION for KMS/secret store remains `TO BE DECIDED`, 006/074), never baked in.

## Scope
- **Applies To**: Both
- **Components**: API runtime image (Flask app + background Scheduler/Delivery worker process model per ARCHITECTURE assumption); SPA build + static-serve image.
- **Actors**: CI build pipeline; container runtime/orchestrator (orchestrator `TO BE DECIDED`).
- **Data Classification**: Internal (image layers MUST contain no Restricted data and no secrets).

## Security Context
- **Defense Layer**: Architecture / Deployment hardening (least privilege at the container boundary)
- **Threat(s) Addressed**: Privilege escalation from a root runtime (CWE-250), secret exposure baked into layers (CWE-798/CWE-540), enlarged attack surface from build tools/debug servers in production (CWE-489 active debug code). STRIDE: Elevation of Privilege, Information Disclosure, Tampering.
- **Trust Boundary**: The container image boundary — what ships to any cloud. A hardened image limits blast radius if a process is compromised and prevents the runtime from holding build-time authority.
- **Zero Trust Consideration**: The runtime is granted only what it needs to run (non-root, minimal libs); it is not trusted with a toolchain or embedded credentials. Secrets are fetched at runtime under least privilege, never shipped.

## Standards Alignment
- **OWASP ASVS**: V14.1 (build/deploy config), V14.2 (dependency/runtime hardening)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: CM-6 (configuration settings), CM-7 (least functionality), SA-15
- **NIST SP 800-207**: least-privilege workload identity at the container boundary
- **Regulatory**: n/a
- **Other**: SECURITY §8 (Docker hardening, Flask hardening), `SEC-3.2`, `SEC-9.1`, `SEC-9.3` (digest pinning aligns with SBOM/integrity in 004)

## Acceptance Criteria
1. **AC-01**: Given the built runtime image, when inspected, then the default/entrypoint user is a non-root UID and the process does not run as UID 0.
2. **AC-02**: Given the Dockerfile, when reviewed, then it is multi-stage and the runtime stage contains no compiler/build toolchain and no dev/test dependencies.
3. **AC-03**: Given the base image reference, when checked, then it is a minimal image pinned by digest (not a floating `latest` tag).
4. **AC-04 (negative)**: Given an attempt to pass a secret as a `--build-arg` or `ENV`, when the image is built and history is inspected, then no secret value is present in any layer, build arg, or image history.
5. **AC-05 (negative)**: Given the API runtime image, when started, then Flask `debug` is False, the Werkzeug debugger/PIN is unreachable, and no dev server or debug endpoint is exposed.
6. **AC-06 (negative)**: Given an image scan, when run in CI, then no high-severity OS/package CVE introduced by the chosen base blocks merge unresolved (ties to 003 SCA gate).

## Failure Behavior
- **On Invalid Input**: A build that requires a secret build arg MUST fail the build rather than proceed with a placeholder; reject over substitute.
- **On System Error**: Fail closed — if the runtime cannot drop to the non-root user or cannot obtain its runtime secret from the secret store, the container MUST refuse to start rather than run with elevated privilege or without required config.
- **Alerting**: CI image scan (003) raises on high-severity findings; a container failing to start non-root surfaces as an orchestration health failure.

## Test Strategy
- **Unit Tests**: n/a (declarative Dockerfile). Lint the Dockerfile (e.g. a Dockerfile linter) as a static check.
- **Integration Tests**: Build both images in CI; run a smoke container and assert the effective user is non-root and the app starts with `debug=False`.
- **Security Tests**: Image vulnerability scan (SCA) on the final image; layer/history inspection asserting no secret material and no build toolchain; confirm no debug server port/endpoint responds.
- **Compliance Tests**: Evidence that base images are digest-pinned and runtime is non-root, collected as a CI artifact for audit.
- **Coverage Target**: ≥ 80% branch coverage applies to application code, not Dockerfiles; the hardening checks above MUST all pass as gating CI steps.

## Dependencies
- **Upstream**: 001 (module roots the images build from).
- **Downstream**: 003 (CI builds/scans these images), 004 (SBOM generated from the pinned image + manifests), all deployment work.
- **External**: A container registry and minimal base image (vendor `TO BE DECIDED`; keep selection behind the digest-pinned reference). Runtime secret store / KMS is `TO BE DECIDED` (006/074) — secrets injected at runtime, not built in.

## Implementation Notes
- **Constraints**: Multi-stage builds only; runtime layer minimal. No infrastructure decision (orchestrator, registry, cloud) is resolved here — keep them behind the image contract. Background Scheduler/Delivery worker process layout is an ARCHITECTURE assumption (shared vs split image is a deployment detail, not decided here).
- **Anti-Patterns**: MUST NOT run as root; MUST NOT use a floating/un-pinned base tag; MUST NOT install gcc/build-essential/dev dependencies into the runtime layer; MUST NOT `COPY` a `.env`, key, or credential into any layer; MUST NOT pass secrets via `ARG`/`ENV`; MUST NOT set Flask `debug=True` or expose the Werkzeug debugger; MUST NOT hard-code `SECRET_KEY` (source it from the secret store at runtime, SECURITY §8).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Well-trodden container-hardening patterns with clear, checkable rules; a strong generalist code model handles multi-stage Dockerfiles reliably. Mandatory human security review of the final image layers (no-secret, non-root, no-toolchain) before merge.
