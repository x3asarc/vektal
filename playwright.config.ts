import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E harness for Shopify Multi-Supplier Platform.
 * Tests run against the local Next.js dev server (port 3000).
 * Browser evidence (screenshots + traces) are first-class artifacts — stored in test-results/.
 *
 * Run: npm --prefix frontend run test:e2e
 * Run (headed): npm --prefix frontend run test:e2e:headed
 * Run (CI): npm --prefix frontend run test:e2e:ci
 */
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/*.e2e.ts",

  /* Fail fast — stop on first failure in CI */
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,

  /* Reporter: list in dev, html+junit in CI */
  reporter: process.env.CI
    ? [
        ["list"],
        ["html", { outputFolder: "test-results/playwright-report", open: "never" }],
        ["junit", { outputFile: "test-results/playwright-results.xml" }],
      ]
    : [["list"], ["html", { open: "on-failure" }]],

  /* Browser evidence — screenshots and traces always captured */
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",

    /* Screenshot on failure — proof artifact */
    screenshot: "only-on-failure",

    /* Full trace on first retry — includes network, console, DOM snapshot */
    trace: "on-first-retry",

    /* Video on failure in CI */
    video: process.env.CI ? "on-first-retry" : "off",

    /* Reasonable timeouts */
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  outputDir: "test-results/playwright-artifacts",

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    /* Uncomment for cross-browser coverage:
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
    },
    */
  ],

  /* Dev server — starts Next.js before tests, tears down after */
  webServer: {
    command: "npm --prefix frontend run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
  },

  /* Global setup/teardown hooks (auth state, seed data) */
  // globalSetup: "./tests/e2e/global-setup.ts",
  // globalTeardown: "./tests/e2e/global-teardown.ts",
});
