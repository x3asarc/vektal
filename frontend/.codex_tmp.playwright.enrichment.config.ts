import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: ".codex_tmp.enrichment-diag.spec.ts",
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "https://app.vektal.systems",
    screenshot: "off",
    trace: "off",
    launchOptions: {
      args: ["--host-resolver-rules=MAP app.vektal.systems 89.167.74.58,EXCLUDE localhost"],
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
