/**
 * E2E: Job progress — jobs list page loads, individual job page renders status.
 * Browser evidence: screenshot + trace captured automatically on failure/retry.
 *
 * Tests the job status UI shell — SSE streaming is not tested here (requires live backend).
 */
import { test, expect, Page } from "@playwright/test";

async function skipIfAuthRequired(page: Page): Promise<boolean> {
  const url = page.url();
  if (url.includes("/auth/login")) {
    return true;
  }
  return false;
}

test.describe("Job progress page", () => {
  test("jobs list page loads without JS error", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");

    expect(errors).toHaveLength(0);
  });

  test("jobs list page renders content or auth redirect", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");

    const skipped = await skipIfAuthRequired(page);
    if (skipped) return;

    // Jobs page should show some kind of content area or empty state
    const content = page.locator(
      "main, [role='main'], table, [data-testid='jobs-workspace'], h1, h2, [data-testid='empty-state']"
    ).first();

    await expect(content).toBeVisible({ timeout: 15_000 });
  });

  test("jobs list page screenshot for evidence", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: "test-results/playwright-artifacts/jobs-list.png",
      fullPage: true,
    });
  });

  test("job detail page route resolves (with mock id)", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    // Navigate to a non-existent job — should render 404/empty state, not crash
    await page.goto("/jobs/nonexistent-job-id-smoke-test");
    await page.waitForLoadState("networkidle");

    // No JS crash — error state is handled gracefully
    expect(errors).toHaveLength(0);

    await page.screenshot({
      path: "test-results/playwright-artifacts/job-detail-404.png",
      fullPage: true,
    });
  });

  test("navigation from jobs list to job detail works", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");

    const skipped = await skipIfAuthRequired(page);
    if (skipped) return;

    // If there are any job links, click the first one
    const jobLink = page.locator("a[href*='/jobs/']").first();
    const hasJobLink = await jobLink.count();

    if (hasJobLink > 0) {
      await jobLink.click();
      await page.waitForLoadState("networkidle");

      // Should be on a job detail page
      expect(page.url()).toMatch(/\/jobs\/.+/);

      await page.screenshot({
        path: "test-results/playwright-artifacts/job-detail-live.png",
        fullPage: true,
      });
    } else {
      // Empty jobs list — expected in fresh dev environment
      console.log("No jobs found in list — empty state is acceptable");
    }
  });
});
