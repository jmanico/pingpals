# Pingpals SPA — hardened multi-stage image (REQ-FND-002, SECURITY.md §8)
#
#   - build stage compiles the React 19 bundle; runtime serves static files only
#   - runtime = nginx-unprivileged (non-root, listens on 8080) — NO build toolchain (AC-01/AC-02)
#   - minimal, DIGEST-PINNED bases (SEC-9.1/9.3); integrity-verified `npm ci` (REQ-FND-004)
#   - no secrets in layers / build args (SEC-3.2)

# ---- Builder: produce the static client bundle ----
FROM node:22-bookworm-slim@sha256:d9f850096136edbc402debdd8729579a288aac64574ada0ff4db26b6ae58b0b2 AS builder

WORKDIR /build
ENV NODE_ENV=production

# `npm ci` installs strictly from package-lock.json with per-package integrity hashes (REQ-FND-004).
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY tsconfig.json vite.config.ts index.html ./
COPY src ./src
RUN npm run build

# ---- Runtime: non-root static server, no Node toolchain ----
FROM nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0 AS runtime

# Image already runs as the non-root `nginx` user (uid 101) and listens on 8080.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 8080
