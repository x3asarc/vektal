import { test } from "@playwright/test";

test("enrichment start diagnostics", async ({ page }) => {
  const apiLogs: Array<{ status: number; url: string; body?: string }> = [];
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];

  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  page.on("response", async (resp) => {
    const url = resp.url();
    if (!url.includes("/api/")) return;
    let body = "";
    try {
      body = (await resp.text()).slice(0, 400);
    } catch {
      body = "<unreadable>";
    }
    apiLogs.push({ status: resp.status(), url, body });
  });

  await page.goto("/auth/login?force=1");
  await page.fill("#email", "admin@vektal.systems");
  await page.fill("#password", "Vektal!Access2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/dashboard|\/onboarding/, { timeout: 20_000 });

  await page.goto("/enrichment", { waitUntil: "domcontentloaded" });
  console.log(`ENRICHMENT_URL_BEFORE=${page.url()}`);
  const startBtn = page.getByRole("button", { name: /Start dry-run/i });
  console.log(`ENRICHMENT_START_BTN_COUNT=${await startBtn.count()}`);
  console.log(`ENRICHMENT_START_BTN_ENABLED=${await startBtn.isEnabled().catch(() => false)}`);
  const startBtnType = await startBtn.getAttribute("type");
  console.log(`ENRICHMENT_START_BTN_TYPE=${startBtnType}`);
  await page.waitForTimeout(2500);
  await startBtn.click();
  console.log(`ENRICHMENT_URL_AFTER_CLICK=${page.url()}`);

  const started = await page
    .locator('[data-testid="enrichment-run-summary"]')
    .isVisible({ timeout: 20_000 })
    .catch(() => false);
  const errorText = await page.locator("p", { hasText: /failed|error/i }).allTextContents();

  console.log(`ENRICHMENT_STARTED=${started}`);
  console.log(`ENRICHMENT_ERRORS=${JSON.stringify(errorText)}`);
  console.log(`ENRICHMENT_PAGE_ERRORS=${JSON.stringify(pageErrors)}`);
  console.log(`ENRICHMENT_CONSOLE_ERRORS=${JSON.stringify(consoleErrors)}`);
  console.log(`ENRICHMENT_API_LOGS=${JSON.stringify(apiLogs, null, 2)}`);
});
