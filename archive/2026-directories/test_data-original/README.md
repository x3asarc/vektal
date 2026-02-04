# Test Data Files

This directory contains sample CSV files for testing the product creation feature.

## Files

### sample_new_products.csv
Contains 3 products with SKUs that **don't exist** in Shopify.
- Use this to test product creation functionality
- Expected result: All products should be created with status "Created"
- Inventory should be set to 0 units for all

### sample_existing_products.csv
Contains 3 products with SKUs that **already exist** in Shopify.
- Use this to test product update functionality
- Expected result: All products should be updated with status "Updated"
- **Inventory should NOT be modified**

### sample_mixed_products.csv
Contains a mix of new and existing products (3 of each).
- Use this to test the create/update branching logic
- Expected result:
  - New products: status "Created", inventory set
  - Existing products: status "Updated", inventory unchanged

## Before Testing

**IMPORTANT**: Before using these test files:

1. Update the SKUs in the CSV files to match your actual products
2. For `sample_existing_products.csv`, use SKUs that already exist in your Shopify store
3. For `sample_new_products.csv`, use SKUs that DON'T exist in your store
4. Verify your scraper can find product data for these SKUs

## How to Test

1. **Start the Flask app**:
   ```bash
   python src/app.py
   ```

2. **Upload a test CSV**:
   - Navigate to http://localhost:5000
   - Authenticate with Shopify
   - Upload one of the test CSV files

3. **Monitor the job**:
   - Check job progress in the web interface
   - Review job results at `/job/{job_id}`

4. **Verify in Shopify**:
   - Check created products are ACTIVE
   - Verify images uploaded correctly
   - Confirm inventory = 0 for new products
   - Confirm inventory unchanged for existing products

5. **Run safety audit**:
   ```bash
   sqlite3 data/scraper.db < safety_audit.sql
   ```

   The critical query should return **0 rows**.

## Expected Results

### For New Products
- `status = "Created"`
- `product_created = 1`
- `inventory_set = 1`
- `inventory_quantity = 0`
- Product exists in Shopify as ACTIVE

### For Existing Products
- `status = "Updated"`
- `product_created = 0`
- `inventory_set = 0`
- Product metadata updated in Shopify
- Inventory levels unchanged

### Safety Check
```sql
SELECT * FROM job_results
WHERE inventory_set = 1 AND product_created = 0;
```
**Must return 0 rows!**
