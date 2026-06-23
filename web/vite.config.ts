import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// React 19 client-only SPA build (no SSR — FE §9). Full app scaffold lands in issue 054.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reportsDirectory: "coverage",
    },
  },
});
