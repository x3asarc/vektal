const scraper = require('./universal_vendor_scraper/scraper');
const dryRun = require('./universal_vendor_scraper/integration/dry-run');
const fs = require('fs');

/**
 * Test the universal scraper with 5 vendors
 */
async function testAllVendors() {
  // Load test SKUs
  const testData = JSON.parse(fs.readFileSync('test_skus.json', 'utf8'));

  console.log('='.repeat(70));
  console.log('UNIVERSAL VENDOR SCRAPER - Testing with Retry Logic');
  console.log('='.repeat(70));
  console.log('');

  const allResults = [];

  for (const product of testData) {
    console.log(`\n${'='.repeat(70)}`);
    console.log(`Testing: ${product.vendor} - ${product.sku}`);
    console.log(`Expected: ${product.title}`);
    console.log('='.repeat(70));

    try {
      // Scrape with retry
      const result = await scraper.scrapeWithRetry(
        product.vendor,
        product.sku,
        product.title
      );

      if (result.success) {
        console.log(`\n✓ SUCCESS via ${result.strategy}`);
        console.log(`Attempts: ${result.attempts.length}`);

        // Generate dry run
        const vendorConfig = require(`./universal_vendor_scraper/vendors/${product.vendor.toLowerCase().replace(/\s+/g, '-')}`);
        const dryRunData = dryRun.generateDryRun(
          result.data,
          vendorConfig,
          0,  // inventory quantity (set to 0 for now)
          product.title
        );

        // Display dry run
        const isReady = dryRun.displayDryRun(dryRunData);

        allResults.push({
          vendor: product.vendor,
          sku: product.sku,
          status: 'success',
          strategy: result.strategy,
          attempts: result.attempts.length,
          ready_to_push: isReady,
          data: result.data,
          dry_run: dryRunData
        });
      } else {
        console.log(`\n✗ FAILED after ${result.attempts.length} attempts`);
        result.attempts.forEach(a => {
          console.log(`  Attempt ${a.attempt} (${a.strategy}): ${a.status}`);
        });

        allResults.push({
          vendor: product.vendor,
          sku: product.sku,
          status: 'failed',
          attempts: result.attempts,
          needs_manual_review: result.needsManualReview,
          last_scraped_data: result.lastScrapedData  // Include the actual scraped data
        });
      }
    } catch (error) {
      console.log(`\n✗ ERROR: ${error.message}`);
      allResults.push({
        vendor: product.vendor,
        sku: product.sku,
        status: 'error',
        error: error.message
      });
    }

    // Rate limiting between vendors
    await new Promise(resolve => setTimeout(resolve, 3000));
  }

  // Summary
  console.log('\n' + '='.repeat(70));
  console.log('FINAL SUMMARY');
  console.log('='.repeat(70));

  const successCount = allResults.filter(r => r.status === 'success').length;
  const readyCount = allResults.filter(r => r.ready_to_push).length;

  console.log(`\nTotal Tests: ${allResults.length}`);
  console.log(`Successful Scrapes: ${successCount}/${allResults.length}`);
  console.log(`Ready to Push: ${readyCount}/${allResults.length}`);
  console.log('');

  allResults.forEach(r => {
    const statusIcon = r.status === 'success' ? '✓' : '✗';
    const readyIcon = r.ready_to_push ? '✓' : '✗';
    console.log(`${statusIcon} ${r.vendor} (${r.sku}) - Ready: ${readyIcon}`);
    if (r.strategy) {
      console.log(`  Strategy: ${r.strategy} (${r.attempts} attempts)`);
    }
  });

  // Save results
  const resultsPath = dryRun.saveDryRun(allResults, 'test-results.json');
  console.log(`\nResults saved to: ${resultsPath}`);

  return allResults;
}

// Run test
testAllVendors()
  .then(() => {
    console.log('\n✓ Test complete!');
    process.exit(0);
  })
  .catch(error => {
    console.error('\n✗ Test failed:', error);
    process.exit(1);
  });
