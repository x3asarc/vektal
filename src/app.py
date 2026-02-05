"""
Shopify Multi-Supplier Scraper App
Flask backend with Shopify OAuth integration
"""
import os
import sys

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hmac
import hashlib
import requests
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
from dotenv import load_dotenv
import sqlite3
from threading import Thread
import time

# Local imports
from utils.pentart_db import PentartDatabase
from src.core.paths import DB_PATH
from src.core.secrets import get_secret

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='web/static', template_folder='web/templates')
app.secret_key = get_secret('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Shopify App Configuration
SHOPIFY_API_KEY = get_secret('SHOPIFY_API_KEY') or os.getenv('SHOPIFY_CLIENT_ID')
SHOPIFY_API_SECRET = get_secret('SHOPIFY_API_SECRET') or os.getenv('SHOPIFY_CLIENT_SECRET')
SHOPIFY_API_SCOPES = 'read_products,write_products,read_inventory,write_inventory,write_files'
SHOPIFY_API_VERSION = os.getenv('API_VERSION', '2024-01')
APP_URL = os.getenv('APP_URL', 'http://localhost:5000')

def init_db():
    """Initialize SQLite database for jobs and results."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Jobs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_domain TEXT NOT NULL,
            status TEXT NOT NULL,
            total_products INTEGER,
            processed INTEGER DEFAULT 0,
            successful INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            created_count INTEGER DEFAULT 0,
            updated_count INTEGER DEFAULT 0,
            inventory_set_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            csv_filename TEXT
        )
    ''')
    
    # Job results table
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            handle TEXT,
            sku TEXT,
            vendor TEXT,
            status TEXT,
            image_url TEXT,
            price REAL,
            error_message TEXT,
            product_created BOOLEAN DEFAULT 0,
            product_id TEXT,
            variant_id TEXT,
            inventory_set BOOLEAN DEFAULT 0,
            inventory_quantity INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
    ''')

    # Pentart products catalog table
    c.execute('''
        CREATE TABLE IF NOT EXISTS pentart_products (
            id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            article_number TEXT UNIQUE,
            ean TEXT,
            product_weight REAL,
            density REAL,
            product_volume REAL,
            inner_qty TEXT,
            inner_weight REAL,
            pcs_per_carton REAL,
            carton_weight REAL,
            carton_size TEXT,
            packaging_mat_weight REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Indexes for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_article_number ON pentart_products(article_number)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_ean ON pentart_products(ean)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_description ON pentart_products(description)')

    # Migration: Add new columns to existing databases
    try:
        # Check if new columns exist, add if not
        c.execute("PRAGMA table_info(job_results)")
        columns = [col[1] for col in c.fetchall()]

        if 'product_created' not in columns:
            c.execute('ALTER TABLE job_results ADD COLUMN product_created BOOLEAN DEFAULT 0')
        if 'product_id' not in columns:
            c.execute('ALTER TABLE job_results ADD COLUMN product_id TEXT')
        if 'variant_id' not in columns:
            c.execute('ALTER TABLE job_results ADD COLUMN variant_id TEXT')
        if 'inventory_set' not in columns:
            c.execute('ALTER TABLE job_results ADD COLUMN inventory_set BOOLEAN DEFAULT 0')
        if 'inventory_quantity' not in columns:
            c.execute('ALTER TABLE job_results ADD COLUMN inventory_quantity INTEGER DEFAULT 0')

        # Check jobs table
        c.execute("PRAGMA table_info(jobs)")
        job_columns = [col[1] for col in c.fetchall()]

        if 'created_count' not in job_columns:
            c.execute('ALTER TABLE jobs ADD COLUMN created_count INTEGER DEFAULT 0')
        if 'updated_count' not in job_columns:
            c.execute('ALTER TABLE jobs ADD COLUMN updated_count INTEGER DEFAULT 0')
        if 'inventory_set_count' not in job_columns:
            c.execute('ALTER TABLE jobs ADD COLUMN inventory_set_count INTEGER DEFAULT 0')

        conn.commit()
    except Exception as e:
        print(f"Migration warning: {e}")

    conn.commit()
    conn.close()

init_db()

# Import scraping functions from image_scraper
from src.core.image_scraper import (
    scrape_product_info, ShopifyClient,
    load_processed_skus, clean_sku,
    DEFAULT_COUNTRY_OF_ORIGIN, get_hs_code
)

@app.route('/')
def index():
    """Main app page - will be embedded in Shopify."""
    # Check if authenticated
    if not session.get('shop') or not session.get('access_token'):
        # Redirect to auth if not authenticated
        shop = request.args.get('shop')
        if shop:
            return redirect(f'/auth/shopify?shop={shop}')
        return render_template('auth_required.html')
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})

@app.route('/auth/shopify')
def shopify_auth():
    """Initiate Shopify OAuth flow."""
    shop = request.args.get('shop')
    if not shop:
        return jsonify({'error': 'Missing shop parameter'}), 400
    
    # Generate state for CSRF protection
    state = os.urandom(16).hex()
    session['oauth_state'] = state
    session['shop'] = shop
    
    # Build authorization URL
    auth_url = (
        f"https://{shop}/admin/oauth/authorize?"
        f"client_id={SHOPIFY_API_KEY}&"
        f"scope={SHOPIFY_API_SCOPES}&"
        f"redirect_uri={APP_URL}/auth/callback&"
        f"state={state}"
    )
    
    return redirect(auth_url)

@app.route('/auth/callback')
def shopify_callback():
    """Handle Shopify OAuth callback."""
    code = request.args.get('code')
    state = request.args.get('state')
    shop = request.args.get('shop')
    
    # Verify state
    if state != session.get('oauth_state'):
        return jsonify({'error': 'Invalid state parameter'}), 400
    
    # Exchange code for access token
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        'client_id': SHOPIFY_API_KEY,
        'client_secret': SHOPIFY_API_SECRET,
        'code': code
    }
    
    try:
        response = requests.post(token_url, json=payload)
        response.raise_for_status()
        data = response.json()
        access_token = data.get('access_token')
        
        # Store access token in session (in production, use database)
        session['shop'] = shop
        session['access_token'] = access_token
        
        # Redirect to app
        return redirect(f'/')
    except Exception as e:
        return jsonify({'error': f'Authentication failed: {str(e)}'}), 500

def verify_webhook(data, hmac_header):
    """Verify Shopify webhook signature."""
    if not hmac_header:
        return False
    calculated_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(calculated_hmac, hmac_header)

@app.route('/webhooks/orders/create', methods=['POST'])
def webhook_orders_create():
    """Handle order creation webhook (example)."""
    data = request.get_data(as_text=True)
    hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
    
    if not verify_webhook(data, hmac_header):
        return jsonify({'error': 'Invalid webhook signature'}), 401
    
    # Process webhook data
    order_data = json.loads(data)
    # Add your webhook processing logic here
    
    return jsonify({'status': 'ok'}), 200

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get authentication status."""
    shop = session.get('shop')
    return jsonify({
        'authenticated': bool(shop and session.get('access_token')),
        'shop': shop
    })

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get all jobs for the current shop."""
    shop = session.get('shop')
    if not shop:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM jobs 
        WHERE shop_domain = ? 
        ORDER BY created_at DESC 
        LIMIT 50
    ''', (shop,))
    
    jobs = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify({'jobs': jobs})

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get specific job details."""
    shop = session.get('shop')
    if not shop:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM jobs WHERE id = ? AND shop_domain = ?', (job_id, shop))
    job = c.fetchone()
    
    if not job:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404
    
    # Get results for this job
    c.execute('''
        SELECT * FROM job_results 
        WHERE job_id = ? 
        ORDER BY created_at DESC
    ''', (job_id,))
    
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify({
        'job': dict(job),
        'results': results
    })

@app.route('/job/<int:job_id>')
def job_detail_page(job_id):
    """Job detail page."""
    return render_template('job_detail.html')

@app.route('/api/pipeline/dry-run', methods=['POST'])
def pipeline_dry_run():
    # Run unified pipeline dry-run for a single identifier.
    shop = session.get('shop')
    access_token = session.get('access_token')

    if not shop or not access_token:
        return jsonify({'error': 'Not authenticated'}), 401

    payload = request.get_json(silent=True) or {}
    identifier = payload.get('identifier') or {}
    selected_product = payload.get('selected_product')

    from src.core.pipeline import process_identifier, process_with_product

    context = {
        'shop_domain': shop,
        'access_token': access_token,
        'api_version': SHOPIFY_API_VERSION,
    }

    if selected_product:
        result = process_with_product(identifier, selected_product, mode='web', context=context)
    else:
        result = process_identifier(identifier, mode='web', context=context)

    return jsonify(result)


@app.route('/api/pipeline/push', methods=['POST'])
def pipeline_push():
    # Push an approved payload (no re-run).
    shop = session.get('shop')
    access_token = session.get('access_token')

    if not shop or not access_token:
        return jsonify({'error': 'Not authenticated'}), 401

    payload = request.get_json(silent=True) or {}

    from src.core.pipeline import apply_payload_with_context

    context = {
        'shop_domain': shop,
        'access_token': access_token,
        'api_version': SHOPIFY_API_VERSION,
    }

    result = apply_payload_with_context(payload, context=context)
    return jsonify(result)


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create a new scraping job from uploaded CSV."""
    shop = session.get('shop')
    access_token = session.get('access_token')
    
    if not shop or not access_token:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        filepath = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)
        
        # Read CSV
        df = pd.read_csv(filepath)
        required_columns = ['Handle', 'SKU', 'Vendor']
        if not all(col in df.columns for col in required_columns):
            return jsonify({
                'error': f'CSV must contain columns: {", ".join(required_columns)}'
            }), 400
        
        # Create job record
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO jobs (shop_domain, status, total_products, csv_filename)
            VALUES (?, ?, ?, ?)
        ''', (shop, 'pending', len(df), filename))
        job_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Start background processing
        thread = Thread(target=process_job, args=(job_id, shop, access_token, filepath, df))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'pending',
            'message': 'Job created and processing started'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Error creating job: {str(e)}'}), 500

def process_job(job_id, shop_domain, access_token, csv_path, df):
    """Background job processor - runs scraping in separate thread."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        # Update job status
        c.execute('UPDATE jobs SET status = ? WHERE id = ?', ('processing', job_id))
        conn.commit()

        # Initialize Shopify client with OAuth token
        shopify = ShopifyClient()
        shopify.access_token = access_token
        shopify.shop_domain = shop_domain
        shopify.graphql_endpoint = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        # Skip authenticate() since we have OAuth token

        # SAFETY: Session-scoped tracking - only products created in THIS job
        newly_created_products = set()

        # Get default location once per job for inventory operations
        default_location_id = None
        try:
            default_location_id = shopify.get_default_location()
            if default_location_id:
                print(f"Default location ID: {default_location_id}")
            else:
                print("Warning: Could not get default location - inventory operations will be skipped")
        except Exception as e:
            print(f"Warning: Could not get default location: {e}")

        # Load processed SKUs
        processed_skus = load_processed_skus()

        # Initialize Pentart database for fast lookups
        pentart_db = None
        try:
            pentart_db = PentartDatabase(DB_PATH)
            print(f"Pentart database initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize Pentart database: {e}")

        successful = 0
        failed = 0
        processed = 0
        created_count = 0
        updated_count = 0
        inventory_set_count = 0
        
        for index, row in df.iterrows():
            try:
                raw_sku = row.get("SKU")
                handle = row.get("Handle")
                vendor = row.get("Vendor")
                
                if pd.isna(vendor) or str(vendor).strip() == "":
                    vendor = "Aistcraft"
                
                # Skip if already processed
                if str(raw_sku) in processed_skus:
                    continue
                
                if not raw_sku:
                    continue
                
                clean = clean_sku(raw_sku)

                # Check if Pentart product - use database lookup first
                vendor_normalized = str(vendor).lower().strip()
                is_pentart = "pentart" in vendor_normalized
                db_hit = False

                if is_pentart and pentart_db:
                    # Try database lookup for Pentart products
                    try:
                        db_product = pentart_db.get_by_article_number(clean)
                        if db_product:
                            # Found in database - use this data instead of scraping
                            print(f"  Database hit for Pentart product: {clean}")
                            db_hit = True
                            scrape_data = {
                                "image_url": None,  # Database doesn't have images, still need to scrape for that
                                "scraped_sku": db_product.get("ean"),  # Use EAN as barcode
                                "price": None,  # Database doesn't have prices
                                "title": db_product.get("description"),
                                "country": "HU",  # Pentart is Hungarian
                                "weight": db_product.get("product_weight")  # Extra field for weight
                            }
                        else:
                            print(f"  Pentart product {clean} not found in database, falling back to scraping")
                    except Exception as e:
                        print(f"  Database lookup error for {clean}: {e}")

                # If not Pentart or not found in database, use web scraping
                if not is_pentart or not db_hit:
                    scrape_data = scrape_product_info(clean, vendor)

                # Extract data from scrape_data
                image_url = scrape_data.get("image_url")
                scraped_barcode = scrape_data.get("scraped_sku")
                scraped_price = scrape_data.get("price")
                product_title = scrape_data.get("title")
                hs_code = scrape_data.get("hs_code") or get_hs_code(product_title)
                product_weight = scrape_data.get("weight")  # For database-sourced weight

                status = "Not Found"
                error_message = None
                product_created = False
                inventory_set = False
                inventory_quantity = 0
                product_id = None
                variant_id = None

                # Check if we have enough data to create/update product
                if not (image_url or product_title):
                    # No data from scraper - check if product exists
                    existing_product_id, _, _ = shopify.get_product_by_sku(raw_sku)

                    if existing_product_id:
                        status = "Not Found"  # Existing product, no scrape data
                    else:
                        status = "New Product - Not Found"  # Would create but no data

                    failed += 1

                else:
                    # We have data - check if product exists in Shopify
                    try:
                        existing_product_id, existing_variant_id, current_barcode = shopify.get_product_by_sku(raw_sku)

                        if existing_product_id:
                            # EXISTING PRODUCT - Update path
                            print(f"  Updating existing product: {raw_sku}")
                            product_id = existing_product_id
                            variant_id = existing_variant_id

                            # Delete existing images
                            if image_url:
                                existing_media_ids = shopify.check_product_has_image(product_id)
                                if existing_media_ids:
                                    shopify.delete_product_media(product_id, existing_media_ids)

                                # Upload new image
                                from src.core.image_scraper import clean_product_name
                                alt_text = clean_product_name(product_title)
                                res = shopify.update_product_media(product_id, image_url, alt_text)

                                if res and not res.get("data", {}).get("productCreateMedia", {}).get("userErrors"):
                                    # Update variant metadata
                                    if variant_id:
                                        variant_update = {"id": variant_id}
                                        if scraped_barcode and str(scraped_barcode).strip() != str(raw_sku).strip():
                                            variant_update["barcode"] = str(scraped_barcode)

                                        # Add weight if available
                                        if product_weight:
                                            variant_update["weight"] = float(product_weight)
                                            variant_update["weightUnit"] = "GRAMS"

                                        inventory_item = {}
                                        if scraped_price:
                                            inventory_item["cost"] = str(scraped_price)
                                        inventory_item["countryCodeOfOrigin"] = scrape_data.get("country", DEFAULT_COUNTRY_OF_ORIGIN)
                                        inventory_item["harmonizedSystemCode"] = hs_code
                                        variant_update["inventoryItem"] = inventory_item

                                        shopify.update_product_variants(product_id, [variant_update])

                                    status = "Updated"
                                    updated_count += 1
                                    successful += 1
                                else:
                                    error_message = "Failed to upload image"
                                    failed += 1

                        else:
                            # NEW PRODUCT - Create path
                            print(f"  Creating new product: {raw_sku}")

                            # Create product as DRAFT
                            new_product_id, new_variant_id, inventory_item_id = shopify.create_product(
                                title=product_title or f"Product {raw_sku}",
                                vendor=vendor,
                                sku=raw_sku,
                                barcode=scraped_barcode,
                                price=scraped_price,
                                weight=product_weight,
                                country=scrape_data.get("country", DEFAULT_COUNTRY_OF_ORIGIN),
                                hs_code=hs_code,
                                category=None
                            )

                            if new_product_id:
                                product_id = new_product_id
                                variant_id = new_variant_id
                                product_created = True
                                newly_created_products.add(product_id)  # Track for safety

                                # Upload image if available
                                if image_url:
                                    from src.core.image_scraper import clean_product_name
                                    alt_text = clean_product_name(product_title)
                                    res = shopify.update_product_media(product_id, image_url, alt_text)

                                    if res and res.get("data", {}).get("productCreateMedia", {}).get("userErrors"):
                                        error_message = f"Image upload warning: {res['data']['productCreateMedia']['userErrors']}"

                                # SAFETY: Only set inventory for newly created products
                                if product_id in newly_created_products and default_location_id and inventory_item_id:
                                    initial_quantity = 0  # Default per user requirement
                                    if shopify.set_inventory_level(inventory_item_id, default_location_id, initial_quantity):
                                        inventory_set = True
                                        inventory_quantity = initial_quantity
                                        inventory_set_count += 1
                                        print(f"  Inventory set to {initial_quantity} units")

                                # Activate product after all data is populated
                                if shopify.activate_product(product_id):
                                    print(f"  Product activated")

                                status = "Created"
                                created_count += 1
                                successful += 1
                            else:
                                error_message = "Failed to create product"
                                failed += 1

                    except Exception as e:
                        error_message = str(e)
                        status = "Error"
                        failed += 1

                # Save result with new columns
                c.execute('''
                    INSERT INTO job_results
                    (job_id, handle, sku, vendor, status, image_url, price, error_message,
                     product_created, product_id, variant_id, inventory_set, inventory_quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (job_id, handle, raw_sku, vendor, status, image_url, scraped_price, error_message,
                      product_created, product_id, variant_id, inventory_set, inventory_quantity))
                
                processed += 1

                # Update job progress with new counters
                c.execute('''
                    UPDATE jobs
                    SET processed = ?, successful = ?, failed = ?,
                        created_count = ?, updated_count = ?, inventory_set_count = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (processed, successful, failed, created_count, updated_count, inventory_set_count, job_id))
                conn.commit()
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                error_message = str(e)
                c.execute('''
                    INSERT INTO job_results 
                    (job_id, handle, sku, vendor, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (job_id, row.get("Handle", ""), row.get("SKU", ""), row.get("Vendor", ""), "Error", error_message))
                failed += 1
                processed += 1
                conn.commit()
        
        # Mark job as complete
        c.execute('UPDATE jobs SET status = ? WHERE id = ?', ('completed', job_id))
        conn.commit()
        
    except Exception as e:
        c.execute('UPDATE jobs SET status = ? WHERE id = ?', ('failed', job_id))
        conn.commit()
    finally:
        conn.close()

@app.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running job."""
    shop = session.get('shop')
    if not shop:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE jobs SET status = ? WHERE id = ? AND shop_domain = ?', 
              ('cancelled', job_id, shop))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Job cancelled'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
