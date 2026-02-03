const scraper = require('./universal_vendor_scraper/scraper');

/**
 * Debug Pentart with improved product link selectors
 */
async function debugPentart() {
  const product = {
    vendor: "Pentart",
    sku: "2493",
    title: "Pentart Grundierfarbe 100ml"
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

    if (result.success) {
      console.log('\n--- SCRAPED DATA ---');
      console.log('Title:', result.data.title);
      console.log('URL:', result.data.url);
      console.log('Price:', result.data.price);
      console.log('Reference:', result.data.reference);
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
        console.log('Price:', result.lastScrapedData.price);
        console.log('Reference:', result.lastScrapedData.reference);
      }
    }

  } catch (error) {
    console.error('\nError:', error.message);
  }
}

debugPentart()
  .then(() => {
    console.log('\nDebug complete!');
    process.exit(0);
  })
  .catch(error => {
    console.error('Debug failed:', error);
    process.exit(1);
  });
