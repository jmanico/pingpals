# Pingpals API — hardened multi-stage image (REQ-FND-002, SECURITY.md §8)
#
# Invariants enforced here:
#   - non-root runtime user (AC-01)                       CWE-250
#   - multi-stage; NO build toolchain / dev deps in the runtime layer (AC-02)
#   - minimal, DIGEST-PINNED base image                   SEC-9.1 / SEC-9.3
#   - integrity-verified install (`pip --require-hashes`) REQ-FND-004
#   - no secrets baked in, no secret build args, no debug server  SEC-3.2 / SECURITY §8

# ---- Builder: resolve deps into an isolated venv (no toolchain leaks to runtime) ----
FROM python:3.12-slim-bookworm@sha256:76d4b7b6305788c6b4c6a19d6a22a3921bf802e9af4d5e1e5bd771208dba74bf AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Hash-pinned runtime deps ONLY (no dev/test tooling in the image) — fails closed on any mismatch.
COPY requirements.lock.txt ./
RUN pip install --require-hashes --no-deps -r requirements.lock.txt

# Install the application package itself (source copied last for cache friendliness).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-deps .

# ---- Runtime: minimal, non-root, toolchain-free ----
FROM python:3.12-slim-bookworm@sha256:76d4b7b6305788c6b4c6a19d6a22a3921bf802e9af4d5e1e5bd771208dba74bf AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_DEBUG=0

# Non-root user (uid/gid 10001). The runtime never holds build authority.
RUN groupadd --gid 10001 appuser \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=appuser:appuser src ./src

USER 10001
EXPOSE 8000

# Placeholder entrypoint. The hardened Flask WSGI entrypoint (gunicorn, debug=False, SECRET_KEY
# from the secret store, injected at runtime — never baked) is implemented in issue 018.
CMD ["python", "-c", "print('pingpals-api runtime image ready; app entrypoint lands in issue 018')"]
