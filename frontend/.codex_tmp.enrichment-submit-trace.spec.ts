import { test } from "@playwright/test";

test("enrichment submit trace", async ({ page }) => {
  const reqs: string[] = [];
  const resps: Array<{ url: string; status: number }> = [];

  page.on("request", (req) => {
    if (req.url().includes("/api/")) reqs.push(`${req.method()} ${req.url()}`);
  });
  page.on("response", (resp) => {
    if (resp.url().includes("/api/")) resps.push({ url: resp.url(), status: resp.status() });
  });

  await page.goto("/auth/login?force=1");
  await page.fill("#email", "admin@vektal.systems");
  await page.fill("#password", "Vektal!Access2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/dashboard|\/onboarding/, { timeout: 20_000 });

  await page.goto("/enrichment", { waitUntil: "domcontentloaded" });

  const submitCounter = await page.evaluate(() => {
    (window as { __submitCounter?: number }).__submitCounter = 0;
    const form = document.querySelector('[data-testid="enrichment-run-configurator"] form');
    form?.addEventListener("submit", () => {
      (window as { __submitCounter?: number }).__submitCounter = ((window as { __submitCounter?: number }).__submitCounter ?? 0) + 1;
    });
    return (window as { __submitCounter?: number }).__submitCounter ?? 0;
  });

  console.log(`SUBMIT_COUNT_INIT=${submitCounter}`);
  console.log(`BTN_TEXT_BEFORE=${(await page.getByRole("button", { name: /Start dry-run|Starting/ }).first().textContent())?.trim()}`);

  await page.getByRole("button", { name: /Start dry-run/i }).click();
  await page.waitForTimeout(1500);

  const submitAfter = await page.evaluate(() => (window as { __submitCounter?: number }).__submitCounter ?? 0);
  console.log(`SUBMIT_COUNT_AFTER_CLICK=${submitAfter}`);
  console.log(`BTN_TEXT_AFTER=${(await page.getByRole("button", { name: /Start dry-run|Starting/ }).first().textContent())?.trim()}`);
  console.log(`REQUESTS=${JSON.stringify(reqs, null, 2)}`);
  console.log(`RESPONSES=${JSON.stringify(resps, null, 2)}`);
});
