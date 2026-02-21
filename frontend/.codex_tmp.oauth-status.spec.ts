import { test, expect } from "@playwright/test";

test("oauth status diagnostics", async ({ page }) => {
  await page.goto("/auth/login?force=1");
  await page.fill("#email", "admin@vektal.systems");
  await page.fill("#password", "Vektal!Access2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/dashboard|\/onboarding/, { timeout: 20_000 });

  const response = await page.request.get("/api/v1/oauth/status");
  const status = response.status();
  const body = await response.text();

  console.log(`OAUTH_STATUS_HTTP=${status}`);
  console.log(`OAUTH_STATUS_BODY=${body}`);

  expect(status).toBe(200);
});
