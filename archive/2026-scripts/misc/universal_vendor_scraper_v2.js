const { chromium } = require('playwright');
const fs = require('fs');

// Enhanced vendor configurations
const VENDOR_CONFIGS = {
  paperdesigns: {
    name: "Paperdesigns",
    search_url: "https://paperdesigns.it/en/search?controller=search&s={sku}",
    wait_for: "body",  // Element to wait for
    product_indicators: [
      "article.product-miniature",
      ".product-miniature",
      ".product-item"
    ],
    selectors: {
      product_link: ["article.product-miniature a", ".product-miniature a", "h2 a", "h3 a"],
      title: ["h1.h1", "h1", ".product-title", "h2"],
      price: ['[itemprop="price"]', ".current-price", ".product-price", ".price"],
      image: ['img[itemprop="image"]', ".product-cover img", "img.js-qv-product-cover", ".product-image img"],
      reference: ['[itemprop="sku"]', ".product-reference", ".reference"],
      description: [".product-description", '[itemprop="description"]', "#description"]
    }
  },
  pentart: {
    name: "Pentart",
    search_url: "https://www.pentacolor.eu/kereses?description=0&keyword={sku}",
    wait_for: "body",
    product_indicators: [".product-thumb", ".product-layout", ".product-item"],
    selectors: {
      product_link: [".product-thumb a", ".product-layout a", ".image a"],
      title: ["h1", ".product-title", "h2"],
      price: [".price", ".product-price", ".price-new"],
      image: ["img.img-responsive", ".product-image img", ".image img"],
      reference: [".product-code", ".sku", ".model"],
      description: [".product-description", "#tab-description", ".description"]
    }
  },
  "itd collection": {
    name: "ITD Collection",
    search_url: "https://itdcollection.com/?s={sku}",  // Different search format
    wait_for: "body",
    product_indicators: [".product", ".product-miniature", "article"],
    selectors: {
      product_link: [".product-miniature a", ".product a", "article a", "h2 a"],
      title: ["h1", ".product-title", "h2"],
      price: [".product-price", ".price", ".amount"],
      image: [".product-cover img", ".product-image img", "img"],
      reference: ['[itemprop="sku"]', ".sku", ".product-reference"],
      description: [".product-description", ".description", ".entry-content"]
    }
  },
  aistcraft: {
    name: "AistCraft",
    search_url: "https://aistcraft.com/search?controller=search&s={sku}",
    wait_for: "body",
    product_indicators: [".product-miniature", ".product", "article"],
    selectors: {
      product_link: [".product-miniature a", ".product_img_link", "a.product-thumbnail"],
      title: ["h1", ".product-title", "h2"],
      price: [".product-price", ".price", ".current-price"],
      image: ["#bigpic", ".product-cover img", ".product-image img"],
      reference: [".product-reference", ".reference", '[itemprop="sku"]'],
      description: [".product-description", "#short_description_content", ".description"]
    }
  },
  stamperia: {
    name: "Stamperia",
    search_url: "https://www.stamperia.com/en/?s={sku}",  // WordPress search
    wait_for: "body",
    product_indicators: [".product", "article", ".post"],
    selectors: {
      product_link: [".product a", "article a", ".woocommerce-LoopProduct-link", "h2 a"],
      title: ["h1", ".product_title", ".entry-title", "h2"],
      price: [".price", ".amount", ".woocommerce-Price-amount"],
      image: [".product-cover img", ".wp-post-image", ".product-image img"],
      reference: ['[itemprop="sku"]', ".sku", ".product-reference"],
      description: [".product-description", ".woocommerce-product-details__short-description", ".entry-content"]
    }
  }
};

async function trySelector(page, selectors) {
  for (const selector of selectors) {
    try {
      const elem = await page.$(selector);
      if (elem) return elem;
    } catch (e) {
      continue;
    }
  }
  return null;
}

async function extractText(page, selectors) {
  const elem = await trySelector(page, selectors);
  if (elem) {
    return (await elem.textContent()).trim();
  }
  return null;
}

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

    // Navigate
    await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

    // Wait for page to render
    await page.waitForSelector(config.wait_for, { timeout: 10000 });
    await page.waitForTimeout(3000);  // Extra wait for JS

    // Take initial screenshot
    await page.screenshot({ path: `screenshots/${vendor}_${sku}_search.png` });
    console.log(`[${vendor}] Search page screenshot saved`);

    // Check if products are visible
    let hasProducts = false;
    for (const indicator of config.product_indicators) {
      const count = await page.locator(indicator).count();
      if (count > 0) {
        console.log(`[${vendor}] Found ${count} products using selector: ${indicator}`);
        hasProducts = true;
        break;
      }
    }

    if (!hasProducts) {
      console.log(`[${vendor}] No products found on page`);
      // Save HTML for debugging
      const html = await page.content();
      fs.writeFileSync(`screenshots/${vendor}_${sku}_search.html`, html);
    }

    const currentUrl = page.url();
    let productUrl = currentUrl;

    // If on search results, find product link
    if (!currentUrl.includes('/product/') && !currentUrl.includes('-p-')) {
      const productLink = await trySelector(page, config.selectors.product_link);
      if (productLink) {
        productUrl = await productLink.getAttribute('href');
        if (productUrl && !productUrl.startsWith('http')) {
          const baseUrl = new URL(searchUrl).origin;
          productUrl = baseUrl + productUrl;
        }
        console.log(`[${vendor}] Found product link: ${productUrl}`);
        await page.goto(productUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(3000);
      } else {
        return { error: 'Product not found in search results' };
      }
    }

    // Take product page screenshot
    await page.screenshot({ path: `screenshots/${vendor}_${sku}_product.png` });

    // Extract data
    const data = {
      vendor: config.name,
      sku: sku,
      url: page.url(),
      scraped_at: new Date().toISOString()
    };

    data.title = await extractText(page, config.selectors.title);
    data.price = await extractText(page, config.selectors.price);
    data.reference = await extractText(page, config.selectors.reference);
    data.description = await extractText(page, config.selectors.description);

    // Image
    const imgElem = await trySelector(page, config.selectors.image);
    if (imgElem) {
      let imgUrl = await imgElem.getAttribute('src') || await imgElem.getAttribute('data-src');
      if (imgUrl && !imgUrl.startsWith('http')) {
        const baseUrl = new URL(searchUrl).origin;
        imgUrl = baseUrl + imgUrl;
      }
      data.image_url = imgUrl;
    }

    console.log(`[${vendor}] Extracted: ${data.title || 'No title'}`);

    return data;

  } catch (error) {
    console.log(`[${vendor}] Error: ${error.message}`);
    return { error: error.message };
  } finally {
    await browser.close();
  }
}

// Main execution
async function main() {
  if (!fs.existsSync('screenshots')) {
    fs.mkdirSync('screenshots');
  }

  const testData = JSON.parse(fs.readFileSync('test_skus.json', 'utf8'));

  console.log('='.repeat(70));
  console.log('UNIVERSAL VENDOR SCRAPER V2 - Enhanced Testing');
  console.log('='.repeat(70));
  console.log('');

  const results = [];

  for (const product of testData) {
    console.log(`\n--- Testing ${product.vendor}: ${product.sku} ---`);
    const result = await scrapeProduct(product.vendor, product.sku);

    if (result.error) {
      console.log(`[FAILED] ${result.error}`);
    } else {
      console.log(`[SUCCESS]`);
      console.log(`  Title: ${result.title || 'N/A'}`);
      console.log(`  Price: ${result.price || 'N/A'}`);
      console.log(`  Image: ${result.image_url ? 'Found' : 'N/A'}`);
    }

    results.push({
      vendor: product.vendor,
      sku: product.sku,
      expected_title: product.title,
      ...result
    });

    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  fs.writeFileSync('scraping_results_v2.json', JSON.stringify(results, null, 2));

  console.log('\n' + '='.repeat(70));
  console.log('RESULTS SUMMARY');
  console.log('='.repeat(70));

  let successCount = 0;
  for (const result of results) {
    const status = result.error ? '[FAILED]' : '[SUCCESS]';
    console.log(`${status} ${result.vendor} - ${result.sku}`);
    if (!result.error && result.title) successCount++;
  }

  console.log(`\nSuccess Rate: ${successCount}/${results.length}`);
  console.log('Detailed results: scraping_results_v2.json');
  console.log('Screenshots: screenshots/ folder');
}

main().catch(console.error);
