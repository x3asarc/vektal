import { connect, waitForPageLoad } from "@/client.js";

async function main() {
  const client = await connect();
  const page = await client.page("localhost-frontend", { viewport: { width: 1440, height: 900 } });

  await page.goto("http://localhost:3000", { waitUntil: "domcontentloaded" });
  await waitForPageLoad(page);

  const title = await page.title();
  const url = page.url();

  const headings = await page.$$eval("h1,h2,h3", (els) =>
    els.map((el) => ({ tag: el.tagName.toLowerCase(), text: el.textContent?.trim() || "" })).filter((h) => h.text)
  );

  const navLinks = await page.$$eval("nav a", (els) =>
    els.map((el) => ({ text: el.textContent?.trim() || "", href: el.getAttribute("href") || "" })).filter((l) => l.text || l.href)
  );

  const buttons = await page.$$eval("button,[role='button']", (els) =>
    els.map((el) => ({ text: el.textContent?.trim() || "", ariaLabel: el.getAttribute("aria-label") || "" })).filter((b) => b.text || b.ariaLabel)
  );

  const inputs = await page.$$eval("input,select,textarea", (els) =>
    els.map((el) => ({
      tag: el.tagName.toLowerCase(),
      type: (el.getAttribute("type") || ""),
      name: el.getAttribute("name") || "",
      placeholder: el.getAttribute("placeholder") || "",
      ariaLabel: el.getAttribute("aria-label") || "",
    })).filter((i) => i.name || i.placeholder || i.ariaLabel)
  );

  await page.screenshot({ path: "tmp/dev-browser/localhost-frontend.png", fullPage: true });

  const snapshot = await client.getAISnapshot("localhost-frontend");

  console.log(JSON.stringify({ title, url, headings, navLinks, buttons, inputs }, null, 2));
  console.log("---SNAPSHOT---");
  console.log(snapshot);

  await client.disconnect();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
