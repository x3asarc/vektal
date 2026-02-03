const scraper = require('./universal_vendor_scraper/scraper');
const dryRun = require('./universal_vendor_scraper/integration/dry-run');
const fs = require('fs');

/**
 * Scrape the 4 missing Paperdesigns products
 */
async function scrapeMissingProducts() {
  const missingProducts = [
    { vendor: "Paperdesigns", sku: "views_0009", inventory: 1 },
    { vendor: "Paperdesigns", sku: "views_0167", inventory: 1 },
    { vendor: "Paperdesigns", sku: "views_0084", inventory: 1 },
    { vendor: "Paperdesigns", sku: "rc003", inventory: 1 }
  ];

  console.log('='.repeat(70));
  console.log('SCRAPING MISSING PAPERDESIGNS PRODUCTS');
  console.log('='.repeat(70));
  console.log('');

  const results = [];

  for (const product of missingProducts) {
    console.log(`\n${'='.repeat(70)}`);
    console.log(`Product: ${product.sku}`);
    console.log('='.repeat(70));

    try {
      // Scrape with retry
      const result = await scraper.scrapeWithRetry(
        product.vendor,
        product.sku,
        null  // No expected title - we'll use the vendor's title
      );

      if (result.success) {
        console.log(`\n[SUCCESS] Found product!`);

        // Generate dry run
        const vendorConfig = require('./universal_vendor_scraper/vendors/paperdesigns');
        const dryRunData = dryRun.generateDryRun(
          result.data,
          vendorConfig,
          product.inventory,
          null
        );

        // Display dry run
        const isReady = dryRun.displayDryRun(dryRunData);

        results.push({
          vendor: product.vendor,
          sku: product.sku,
          status: 'success',
          strategy: result.strategy,
          inventory: product.inventory,
          ready_to_push: isReady,
          shopify_data: dryRunData.shopify_data,
          raw_scraped: result.data
        });
      } else {
        console.log(`\n[FAILED] Could not find product`);
        console.log(`Attempts: ${result.attempts.length}`);
        result.attempts.forEach(a => {
          console.log(`  ${a.attempt}. ${a.strategy}: ${a.status}`);
          if (a.error) {
            console.log(`     Error: ${a.error}`);
          }
        });

        results.push({
          vendor: product.vendor,
          sku: product.sku,
          status: 'failed',
          attempts: result.attempts,
          needs_manual_review: true
        });
      }
    } catch (error) {
      console.log(`\n[ERROR] ${error.message}`);
      results.push({
        vendor: product.vendor,
        sku: product.sku,
        status: 'error',
        error: error.message
      });
    }

    // Rate limiting
    await new Promise(resolve => setTimeout(resolve, 3000));
  }

  // Summary
  console.log('\n' + '='.repeat(70));
  console.log('FINAL SUMMARY');
  console.log('='.repeat(70));

  const successCount = results.filter(r => r.status === 'success').length;
  const readyCount = results.filter(r => r.ready_to_push).length;

  console.log(`\nTotal Products: ${results.length}`);
  console.log(`Successfully Scraped: ${successCount}/${results.length}`);
  console.log(`Ready to Push: ${readyCount}/${results.length}`);
  console.log('');

  results.forEach(r => {
    const statusIcon = r.status === 'success' ? '[OK]' : '[FAIL]';
    const readyIcon = r.ready_to_push ? 'READY' : 'NOT READY';
    console.log(`${statusIcon} ${r.sku} - ${readyIcon}`);
    if (r.strategy) {
      console.log(`    Strategy: ${r.strategy}`);
    }
  });

  // Save results
  const resultsPath = dryRun.saveDryRun(results, 'missing-products-scraped.json');
  console.log(`\nResults saved to: ${resultsPath}`);

  return results;
}

// Run
scrapeMissingProducts()
  .then(() => {
    console.log('\n[COMPLETE] Scraping finished!');
    process.exit(0);
  })
  .catch(error => {
    console.error('\n[ERROR] Scraping failed:', error);
    process.exit(1);
  });
