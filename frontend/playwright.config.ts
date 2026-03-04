import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.PLAYWRIGHT_PORT ?? 3000);
const WEB_SERVER_COMMAND =
  process.env.PLAYWRIGHT_WEB_SERVER_COMMAND ?? "npm run start";
const WORKERS = Number(process.env.PLAYWRIGHT_WORKERS ?? 1);

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/*.e2e.ts",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: Number.isNaN(WORKERS) ? 1 : WORKERS,
  timeout: 45_000,
  reporter: process.env.CI
    ? [
        ["list"],
        ["html", { outputFolder: "./test-results/playwright-report", open: "never" }],
        ["junit", { outputFile: "./test-results/playwright-results.xml" }],
      ]
    : [["list"], ["html", { outputFolder: "./test-results/playwright-report", open: "on-failure" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
    video: process.env.CI ? "on-first-retry" : "off",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  outputDir: "./test-results/playwright-artifacts",
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: WEB_SERVER_COMMAND,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
