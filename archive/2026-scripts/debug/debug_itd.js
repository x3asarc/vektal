const scraper = require('./universal_vendor_scraper/scraper');

/**
 * Debug script - test ITD Collection with cookie dismissal
 */
async function debugITD() {
  const product = {
    vendor: "ITD Collection",
    sku: "R880",
    title: "Reispapier A4 - London"
  };

  console.log('='.repeat(70));
  console.log(`Testing: ${product.vendor} - ${product.sku}`);
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
      }

      if (a.validation) {
        console.log(`  Valid: ${a.validation.isValid}`);
        console.log(`  Confidence: ${a.validation.confidence}%`);
        if (a.validation.reason) {
          console.log(`  Reason: ${a.validation.reason}`);
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
      console.log('Reference:', result.lastScrapedData.reference);
    }

  } catch (error) {
    console.error('\nError:', error.message);
  }
}

debugITD()
  .then(() => {
    console.log('\nDebug complete!');
    process.exit(0);
  })
  .catch(error => {
    console.error('Debug failed:', error);
    process.exit(1);
  });
