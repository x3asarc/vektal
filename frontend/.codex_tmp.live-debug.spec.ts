import { test, expect } from "@playwright/test";

type Finding = {
  kind: "pageerror" | "console-error" | "api-error" | "route-doc-error";
  route?: string;
  detail: string;
  status?: number;
  url?: string;
};

test("authenticated live discovery pass", async ({ page }) => {
  const findings: Finding[] = [];
  const routes = ["/dashboard", "/jobs", "/search"];

  page.on("pageerror", (err) => {
    findings.push({ kind: "pageerror", route: page.url(), detail: err.message });
  });

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      findings.push({ kind: "console-error", route: page.url(), detail: msg.text() });
    }
  });

  page.on("response", async (resp) => {
    const status = resp.status();
    const url = resp.url();
    if (url.includes("/api/") && status >= 400) {
      let bodySnippet = "";
      try {
        const body = await resp.text();
        bodySnippet = body.slice(0, 220);
      } catch {
        bodySnippet = "<unreadable>";
      }
      findings.push({
        kind: "api-error",
        route: page.url(),
        detail: `API request returned >=400: ${bodySnippet}`,
        status,
        url,
      });
    }
  });

  await page.goto("/auth/login?force=1");
  await page.fill("#email", "admin@vektal.systems");
  await page.fill("#password", "Vektal!Access2026");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.waitForURL(/\/dashboard|\/onboarding/, { timeout: 20_000 });
  expect(page.url()).toMatch(/\/dashboard|\/onboarding/);

  // Deeper chat interaction: send a real message and wait for assistant/error.
  await page.goto("/chat", { waitUntil: "domcontentloaded" });
  await expect(page.locator("#chat-message-input")).toBeVisible({ timeout: 15_000 });
  const assistantBefore = await page.locator('[data-role="assistant"]').count();
  await page.locator("#chat-message-input").fill("ping from playwright live debug");
  await page.locator("#chat-message-input").press("Enter");

  let chatSettled = false;
  for (let i = 0; i < 20; i++) {
    const chatError = page.locator(".chat-error").first();
    if (await chatError.isVisible().catch(() => false)) {
      findings.push({
        kind: "route-doc-error",
        route: "/chat",
        detail: `Chat surfaced UI error: ${(await chatError.textContent()) ?? ""}`.trim(),
      });
      chatSettled = true;
      break;
    }

    const assistantAfter = await page.locator('[data-role="assistant"]').count();
    if (assistantAfter > assistantBefore) {
      const lastAssistant = page.locator('[data-role="assistant"] p').last();
      const lastText = ((await lastAssistant.textContent()) ?? "").trim();
      if (!lastText) {
        findings.push({
          kind: "route-doc-error",
          route: "/chat",
          detail: "Assistant response was created but empty.",
        });
      } else if (lastText.includes("{{") || lastText.includes("}}")) {
        findings.push({
          kind: "route-doc-error",
          route: "/chat",
          detail: `Assistant response contains unresolved template markers: ${lastText.slice(0, 140)}`,
        });
      }
      chatSettled = true;
      break;
    }
    await page.waitForTimeout(800);
  }
  if (!chatSettled) {
    findings.push({
      kind: "route-doc-error",
      route: "/chat",
      detail: "No assistant response or chat error surfaced within timeout.",
    });
  }
  await page.screenshot({
    path: "../test-results/playwright-artifacts-live-debug/chat-interaction.png",
    fullPage: true,
  });

  // Enrichment lifecycle interaction.
  await page.goto("/enrichment", { waitUntil: "domcontentloaded" });
  const startBtn = page.getByRole("button", { name: /Start dry-run/i });
  if (await startBtn.isVisible().catch(() => false)) {
    await startBtn.click();
    await page.waitForTimeout(1800);
    const err = page.locator("p", { hasText: /failed|error/i }).first();
    if (await err.isVisible().catch(() => false)) {
      findings.push({
        kind: "route-doc-error",
        route: "/enrichment",
        detail: `Enrichment surfaced UI error: ${(await err.textContent()) ?? ""}`.trim(),
      });
    } else if (!(await page.locator('[data-testid="enrichment-run-summary"]').isVisible().catch(() => false))) {
      findings.push({
        kind: "route-doc-error",
        route: "/enrichment",
        detail: "No enrichment summary and no explicit UI error after start.",
      });
    }
  } else {
    findings.push({
      kind: "route-doc-error",
      route: "/enrichment",
      detail: "Start dry-run button not visible.",
    });
  }
  await page.screenshot({
    path: "../test-results/playwright-artifacts-live-debug/enrichment-interaction.png",
    fullPage: true,
  });

  for (const route of routes) {
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    const status = response?.status() ?? 0;
    if (status >= 400) {
      findings.push({
        kind: "route-doc-error",
        route,
        detail: "Document request returned >=400",
        status,
        url: response?.url(),
      });
    }

    await page.waitForTimeout(1200);
    await page.screenshot({
      path: `../test-results/playwright-artifacts-live-debug/${route.replace("/", "") || "root"}.png`,
      fullPage: true,
    });
  }

  // Deduplicate noisy repeats.
  const unique = new Map<string, Finding>();
  for (const f of findings) {
    const key = `${f.kind}|${f.route ?? ""}|${f.status ?? ""}|${f.url ?? ""}|${f.detail}`;
    unique.set(key, f);
  }
  const finalFindings = Array.from(unique.values());

  console.log(`LIVE_DEBUG_FINDINGS=${JSON.stringify(finalFindings, null, 2)}`);
  expect(finalFindings).toEqual([]);
});
