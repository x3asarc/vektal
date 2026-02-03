const { chromium } = require('playwright');
const fs = require('fs');

// Vendor configurations from vendor_configs.yaml
const VENDOR_CONFIGS = {
  paperdesigns: {
    name: "Paperdesigns",
    search_url: "https://paperdesigns.it/en/search?controller=search&s={sku}",
    selectors: {
      product_link: "article.product-miniature a.product-thumbnail",
      title: "h1.h1, h1",
      price: '[itemprop="price"], .current-price span',
      image: 'img.js-qv-product-cover, img[itemprop="image"]',
      reference: '[itemprop="sku"]',
      description: '.product-description, [itemprop="description"]'
    }
  },
  pentart: {
    name: "Pentart",
    search_url: "https://www.pentacolor.eu/kereses?description=0&keyword={sku}",
    selectors: {
      product_link: ".product-thumb a",
      title: "h1, .product-title",
      price: ".price, .product-price",
      image: "img.img-responsive, .product-image img",
      reference: ".product-code, .sku",
      description: ".product-description, #tab-description"
    }
  },
  "itd collection": {
    name: "ITD Collection",
    search_url: "https://itdcollection.com/search?controller=search&s={sku}",
    selectors: {
      product_link: ".product-miniature a",
      title: "h1",
      price: ".product-price",
      image: ".product-cover img",
      reference: '[itemprop="sku"]',
      description: ".product-description"
    }
  },
  aistcraft: {
    name: "AistCraft",
    search_url: "https://aistcraft.com/search?controller=search&orderby=position&orderway=desc&search_query={sku}&submit_search=",
    selectors: {
      product_link: ".product-miniature a, .product_img_link",
      title: "h1",
      price: ".product-price, .price",
      image: "#bigpic, .product-cover img",
      reference: ".product-reference, .reference",
      description: ".product-description, #short_description_content"
    }
  },
  stamperia: {
    name: "Stamperia",
    search_url: "https://www.stamperia.com/en/search?controller=search&s={sku}",
    selectors: {
      product_link: ".product-miniature a",
      title: "h1",
      price: ".product-price",
      image: ".product-cover img",
      reference: '[itemprop="sku"]',
      description: ".product-description"
    }
  }
};

async function scrapeProduct(vendor, sku) {
  const config = VENDOR_CONFIGS[vendor.toLowerCase()];
  if (!config) {
    return { error: `Unknown vendor: ${vendor}` };
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  try {
    const searchUrl = config.search_url.replace('{sku}', sku);
    console.log(`[${vendor}] Navigating to: ${searchUrl}`);

    // Navigate with timeout
    await page.goto(searchUrl, { waitUntil: 'networkidle', timeout: 30000 });

    // Wait for page to load
    await page.waitForTimeout(2000);

    // Check if we were redirected to a product page
    const currentUrl = page.url();
    let productUrl = currentUrl;

    // If on search results, find product link
    if (currentUrl.includes('search')) {
      const productLink = await page.$(config.selectors.product_link);
      if (productLink) {
        productUrl = await productLink.getAttribute('href');
        if (productUrl && !productUrl.startsWith('http')) {
          const baseUrl = new URL(searchUrl).origin;
          productUrl = baseUrl + productUrl;
        }
        console.log(`[${vendor}] Found product, navigating to: ${productUrl}`);
        await page.goto(productUrl, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForTimeout(2000);
      } else {
        return { error: 'Product not found in search results' };
      }
    }

    // Extract data
    const data = {
      vendor: config.name,
      sku: sku,
      url: page.url(),
      scraped_at: new Date().toISOString()
    };

    // Title
    try {
      const titleElem = await page.$(config.selectors.title);
      if (titleElem) {
        data.title = (await titleElem.textContent()).trim();
      }
    } catch (e) {
      console.log(`[${vendor}] Could not extract title: ${e.message}`);
    }

    // Price
    try {
      const priceElem = await page.$(config.selectors.price);
      if (priceElem) {
        data.price = (await priceElem.textContent()).trim();
      }
    } catch (e) {
      console.log(`[${vendor}] Could not extract price: ${e.message}`);
    }

    // Image
    try {
      const imgElem = await page.$(config.selectors.image);
      if (imgElem) {
        let imgUrl = await imgElem.getAttribute('src') || await imgElem.getAttribute('data-src');
        if (imgUrl && !imgUrl.startsWith('http')) {
          const baseUrl = new URL(searchUrl).origin;
          imgUrl = baseUrl + imgUrl;
        }
        data.image_url = imgUrl;
      }
    } catch (e) {
      console.log(`[${vendor}] Could not extract image: ${e.message}`);
    }

    // Reference/SKU
    try {
      const refElem = await page.$(config.selectors.reference);
      if (refElem) {
        data.reference = (await refElem.textContent()).trim();
      }
    } catch (e) {
      console.log(`[${vendor}] Could not extract reference: ${e.message}`);
    }

    // Description
    try {
      const descElem = await page.$(config.selectors.description);
      if (descElem) {
        data.description = (await descElem.textContent()).trim().substring(0, 500);
      }
    } catch (e) {
      console.log(`[${vendor}] Could not extract description: ${e.message}`);
    }

    // Screenshot for verification
    await page.screenshot({ path: `screenshots/${vendor}_${sku}.png`, fullPage: false });
    console.log(`[${vendor}] Screenshot saved`);

    return data;

  } catch (error) {
    return { error: error.message };
  } finally {
    await browser.close();
  }
}

// Main execution
async function main() {
  // Create screenshots directory
  if (!fs.existsSync('screenshots')) {
    fs.mkdirSync('screenshots');
  }

  // Read test SKUs
  const testData = JSON.parse(fs.readFileSync('test_skus.json', 'utf8'));

  console.log('='.repeat(70));
  console.log('UNIVERSAL VENDOR SCRAPER - Testing 5 Vendors');
  console.log('='.repeat(70));
  console.log('');

  const results = [];

  for (const product of testData) {
    console.log(`\n--- Testing ${product.vendor}: ${product.sku} ---`);
    const result = await scrapeProduct(product.vendor, product.sku);

    if (result.error) {
      console.log(`[ERROR] ${result.error}`);
    } else {
      console.log(`[SUCCESS] Found product: ${result.title}`);
      console.log(`  Price: ${result.price || 'N/A'}`);
      console.log(`  Image: ${result.image_url ? 'Found' : 'N/A'}`);
    }

    results.push({
      vendor: product.vendor,
      sku: product.sku,
      ...result
    });

    // Delay between vendors
    await new Promise(resolve => setTimeout(resolve, 3000));
  }

  // Save results
  fs.writeFileSync('scraping_results.json', JSON.stringify(results, null, 2));

  console.log('\n' + '='.repeat(70));
  console.log('RESULTS SUMMARY');
  console.log('='.repeat(70));

  let successCount = 0;
  for (const result of results) {
    const status = result.error ? '[FAILED]' : '[SUCCESS]';
    console.log(`${status} ${result.vendor} - ${result.sku}`);
    if (!result.error) successCount++;
  }

  console.log(`\nSuccess Rate: ${successCount}/${results.length}`);
  console.log('Results saved to: scraping_results.json');
  console.log('Screenshots saved to: screenshots/');
}

main().catch(console.error);
