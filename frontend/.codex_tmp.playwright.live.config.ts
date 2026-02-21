import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: ".codex_tmp.live-debug.spec.ts",
  fullyParallel: false,
  retries: 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "../test-results/playwright-report-live-debug", open: "never" }],
  ],
  use: {
    baseURL: "https://app.vektal.systems",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    // Force new server IP to eliminate stale resolver noise during app debugging.
    launchOptions: {
      args: ["--host-resolver-rules=MAP app.vektal.systems 89.167.74.58,EXCLUDE localhost"],
    },
  },
  outputDir: "../test-results/playwright-artifacts-live-debug",
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
