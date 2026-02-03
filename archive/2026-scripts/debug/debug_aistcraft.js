const scraper = require('./universal_vendor_scraper/scraper');

/**
 * Debug AistCraft with AC suffix removal and experimental strategy
 */
async function debugAistCraft() {
  const product = {
    vendor: "AistCraft",
    sku: "45970AC",
    title: "Reispapier 32x45cm - Angels and roses"
  };

  console.log('='.repeat(70));
  console.log(`Testing: ${product.vendor} - ${product.sku}`);
  console.log(`Note: "AC" suffix should be removed for search`);
  console.log('='.repeat(70));

  try {
    const result = await scraper.scrapeWithRetry(
      product.vendor,
      product.sku,
      product.title
    );

    console.log('\n--- RESULT ---');
    console.log('Success:', result.success);

    if (result.success) {
      console.log('\n--- SCRAPED DATA ---');
      console.log('Title:', result.data.title);
      console.log('URL:', result.data.url);
      console.log('Price:', result.data.price);
      console.log('Reference:', result.data.reference);
      console.log('Image:', result.data.image_url);
    } else {
      console.log('\n--- ATTEMPTS ---');
      result.attempts.forEach(a => {
        console.log(`\nAttempt ${a.attempt} (${a.strategy}):`);
        console.log(`  Status: ${a.status}`);

        if (a.scraped_title) {
          console.log(`  Scraped Title: "${a.scraped_title}"`);
        }

        if (a.error) {
          console.log(`  Error: ${a.error}`);
        }
      });

      if (result.lastScrapedData) {
        console.log('\n--- LAST SCRAPED DATA ---');
        console.log('Title:', result.lastScrapedData.title);
        console.log('URL:', result.lastScrapedData.url);
      }
    }

  } catch (error) {
    console.error('\nError:', error.message);
  }
}

debugAistCraft()
  .then(() => {
    console.log('\nDebug complete!');
    process.exit(0);
  })
  .catch(error => {
    console.error('Debug failed:', error);
    process.exit(1);
  });
