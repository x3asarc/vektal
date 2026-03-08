import { test } from '@playwright/test';
import fs from 'fs';

const PAGES = [
  { name: 'dashboard', url: 'http://localhost:3000/dashboard' },
  { name: 'search', url: 'http://localhost:3000/search' },
  { name: 'chat', url: 'http://localhost:3000/chat' },
  { name: 'enrichment', url: 'http://localhost:3000/enrichment' },
];

test('capture all pages for consistency audit', async ({ page }) => {
  // DEV/AUDIT BYPASS: Mock auth and dashboard summary
  await page.addInitScript(() => {
    window.localStorage.setItem('auth_bypass', 'true');
    // Mock user profile
    (window as any).USER_CONTEXT = { id: 'audit-user', role: 'admin' };
  });

  // Mock the dashboard summary API to avoid 401 redirect/error
  await page.route('**/api/v1/ops/dashboard/summary', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_skus: 4250,
        avg_completeness: 84.2,
        healthy_skus: 3100,
        unhealthy_skus: 1150,
        last_ingest_at: '2026-03-07T10:42:11',
        field_coverage: {
          title: 4250,
          description: 2167,
          price: 3910,
          sku: 4250,
          tags: 3102
        },
        store_domain: 'bastelschachtel.at'
      }),
    });
  });

  for (const p of PAGES) {
    try {
      await page.goto(p.url, { waitUntil: 'networkidle' });
      // Wait a bit for any dynamic content/animations
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `.ooda/audit_${p.name}.png`, fullPage: true });
      
      const content = await page.evaluate(() => document.body.innerText);
      fs.writeFileSync(`.ooda/audit_${p.name}.txt`, content);
      
      console.log(`Captured ${p.name}`);
    } catch (e: any) {
      console.error(`Failed to capture ${p.name}: ${e.message}`);
    }
  }
});
