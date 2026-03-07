import { test } from '@playwright/test';
import fs from 'fs';

test('capture dashboard observation', async ({ page }) => {
  await page.goto('http://localhost:3000/dashboard');
  await page.waitForSelector('h1:has-text("Product Data Command Center")');
  
  // Capture screenshot
  await page.screenshot({ path: 'frontend/test-results/dashboard_obs.png', fullPage: true });
  
  // Capture page structure as text/markdown-like
  const content = await page.evaluate(() => document.body.innerText);
  fs.writeFileSync('frontend/test-results/dashboard_obs.txt', content);
  
  // Also get some HTML structure for structural analysis
  const html = await page.content();
  fs.writeFileSync('frontend/test-results/dashboard_obs.html', html);
});
