import { test, expect } from '@playwright/test';

test('dashboard validation', async ({ page }) => {
  // Go to the dashboard directly on the frontend port
  await page.goto('http://localhost:3000/dashboard');

  // Wait for the main title
  await expect(page.locator('h1')).toContainText('Product Data Command Center');
  
  // Wait for the chat dock marker
  await expect(page.locator('text=Operational Control Dock')).toBeVisible();

  // Take a screenshot for analysis
  await page.screenshot({ path: 'test-results/dashboard-validation.png', fullPage: true });
  
  // Log the summary stats if visible
  const stats = await page.locator('.grid.grid-cols-1.md\\:grid-cols-2 >> div').allInnerTexts();
  console.log('Dashboard Stats:', stats);
});
