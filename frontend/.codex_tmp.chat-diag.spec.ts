import { test } from "@playwright/test";

test("chat send diagnostics", async ({ page }) => {
  const apiLogs: Array<{ status: number; url: string; body: string }> = [];
  const consoleErrors: string[] = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  page.on("response", async (resp) => {
    const url = resp.url();
    if (!url.includes("/api/v1/chat")) return;
    let body = "";
    try {
      body = (await resp.text()).slice(0, 500);
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

  await page.goto("/chat", { waitUntil: "domcontentloaded" });
  await page.locator("#chat-message-input").fill("ping from playwright chat diagnostics");
  await page.locator("#chat-message-input").press("Enter");

  await page.waitForTimeout(10000);
  let chatError = "";
  const chatErrorLocator = page.locator(".chat-error").first();
  if (await chatErrorLocator.count()) {
    chatError = ((await chatErrorLocator.textContent()) ?? "").trim();
  }
  let assistantText = "";
  const assistantLocator = page.locator('[data-role="assistant"] p').last();
  if (await assistantLocator.count()) {
    assistantText = ((await assistantLocator.textContent()) ?? "").trim();
  }

  console.log(`CHAT_ERROR=${chatError}`);
  console.log(`CHAT_LAST_ASSISTANT=${assistantText.slice(0, 300)}`);
  console.log(`CHAT_CONSOLE_ERRORS=${JSON.stringify(consoleErrors)}`);
  console.log(`CHAT_API_LOGS=${JSON.stringify(apiLogs, null, 2)}`);
});
