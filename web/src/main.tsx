/**
 * SPA entrypoint (placeholder — REQ-FND-001 reserves the location).
 *
 * The full React 19 client-only application (strict CSP, SRI, Zod validation, UUID keys,
 * AbortController fetch, validateAndSanitizeUrl on every href/src) is the subject of issue 054
 * and the FRONTEND issues. This module only mounts an empty root and loads the design tokens so
 * the build target and token wiring (REQ-FND-005) exist for downstream work.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./tokens/tokens.css";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <main>Pingpals</main>
    </StrictMode>,
  );
}
