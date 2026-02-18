-- Safety Audit Queries for Product Creation Feature
-- Run these queries after processing jobs to verify inventory safety

-- CRITICAL: This query should ALWAYS return ZERO rows
-- If it returns any rows, it means inventory was set on an existing product (CRITICAL BUG)
SELECT
    id,
    job_id,
    sku,
    vendor,
    status,
    product_created,
    inventory_set,
    inventory_quantity,
    created_at
FROM job_results
WHERE inventory_set = 1 AND product_created = 0;

-- Summary: Count of created vs updated products
SELECT
    status,
    COUNT(*) as count,
    SUM(CASE WHEN product_created = 1 THEN 1 ELSE 0 END) as created,
    SUM(CASE WHEN product_created = 0 THEN 1 ELSE 0 END) as updated,
    SUM(CASE WHEN inventory_set = 1 THEN 1 ELSE 0 END) as inventory_set
FROM job_results
GROUP BY status
ORDER BY count DESC;

-- Inventory operations summary
SELECT
    COUNT(*) as total_inventory_operations,
    SUM(CASE WHEN product_created = 1 THEN 1 ELSE 0 END) as on_new_products,
    SUM(CASE WHEN product_created = 0 THEN 1 ELSE 0 END) as on_existing_products
FROM job_results
WHERE inventory_set = 1;

-- Recent job statistics
SELECT
    j.id,
    j.shop_domain,
    j.status,
    j.total_products,
    j.processed,
    j.successful,
    j.failed,
    j.created_count,
    j.updated_count,
    j.inventory_set_count,
    j.created_at
FROM jobs j
ORDER BY j.created_at DESC
LIMIT 10;

-- Products created in latest job
SELECT
    sku,
    vendor,
    status,
    product_created,
    inventory_set,
    inventory_quantity,
    error_message
FROM job_results
WHERE job_id = (SELECT MAX(id) FROM jobs)
  AND product_created = 1
ORDER BY created_at;

-- Products updated in latest job
SELECT
    sku,
    vendor,
    status,
    product_created,
    inventory_set,
    error_message
FROM job_results
WHERE job_id = (SELECT MAX(id) FROM jobs)
  AND status = 'Updated'
ORDER BY created_at;
