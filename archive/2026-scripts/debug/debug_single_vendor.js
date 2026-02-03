const scraper = require('./universal_vendor_scraper/scraper');

/**
 * Debug script - test one vendor to see actual scraped data
 */
async function debugSingleVendor() {
  const product = {
    vendor: "Paperdesigns",
    sku: "animals-0079",
    title: "Reispapier A4 - Wildducks"
  };

  console.log('='.repeat(70));
  console.log(`Testing: ${product.vendor} - ${product.sku}`);
  console.log(`Our Shopify title: ${product.title}`);
  console.log('='.repeat(70));

  try {
    const result = await scraper.scrapeWithRetry(
      product.vendor,
      product.sku,
      product.title
    );

    console.log('\n--- RESULT ---');
    console.log('Success:', result.success);
    console.log('\nAttempts:');

    result.attempts.forEach(a => {
      console.log(`\nAttempt ${a.attempt} (${a.strategy}):`);
      console.log(`  Status: ${a.status}`);

      if (a.scraped_title) {
        console.log(`  Scraped Title: "${a.scraped_title}"`);
        console.log(`  Expected Title: "${product.title}"`);
      }

      if (a.validation) {
        console.log(`  Valid: ${a.validation.isValid}`);
        console.log(`  Confidence: ${a.validation.confidence}%`);
        console.log(`  Reason: ${a.validation.reason || 'N/A'}`);
        if (a.validation.warnings.length > 0) {
          console.log(`  Warnings: ${a.validation.warnings.join(', ')}`);
        }
      }

      if (a.error) {
        console.log(`  Error: ${a.error}`);
      }
    });

    if (result.lastScrapedData) {
      console.log('\n--- LAST SCRAPED DATA ---');
      console.log('Title:', result.lastScrapedData.title);
      console.log('URL:', result.lastScrapedData.url);
      console.log('Price:', result.lastScrapedData.price);
      console.log('Image:', result.lastScrapedData.image_url);
      console.log('Reference/SKU:', result.lastScrapedData.reference);
    }

  } catch (error) {
    console.error('\nError:', error.message);
    console.error(error.stack);
  }
}

debugSingleVendor()
  .then(() => {
    console.log('\nDebug complete!');
    process.exit(0);
  })
  .catch(error => {
    console.error('Debug failed:', error);
    process.exit(1);
  });
