# Quick Setup Guide

## Step 1: Create Shopify App

1. Go to https://partners.shopify.com/
2. Log in or create an account
3. Click "Apps" → "Create app"
4. Choose "Custom app"
5. Name it "Multi-Supplier Scraper"
6. Set **App URL**: `http://localhost:5000` (or your production URL)
7. Set **Allowed redirection URL(s)**: `http://localhost:5000/auth/callback`
8. Click "Create app"
9. Go to "Configuration" tab
10. Under "Admin API integration scopes", enable:
    - `read_products`
    - `write_products`
    - `read_inventory`
    - `write_inventory`
11. Save and note your **API key** and **API secret key**

## Step 2: Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```env
   SHOPIFY_API_KEY=your_api_key_from_step_1
   SHOPIFY_API_SECRET=your_api_secret_from_step_1
   FLASK_SECRET_KEY=generate-a-random-string-here
   APP_URL=http://localhost:5000
   ```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Run the App

```bash
python app.py
```

The app will start on `http://localhost:5000`

## Step 5: Install in Your Store

1. Visit: `http://localhost:5000/auth/shopify?shop=YOUR-STORE.myshopify.com`
   (Replace YOUR-STORE with your actual store name)

2. Click "Install app" when prompted

3. You'll be redirected to the app interface

## Step 6: Use the App

1. Prepare a CSV file with columns: `Handle`, `SKU`, `Vendor`
2. Upload it through the web interface
3. Monitor progress in real-time
4. View detailed results for each job

## For Production

1. Deploy to a hosting service (Heroku, Railway, DigitalOcean, etc.)
2. Update `APP_URL` in `.env` to your production URL
3. Update your Shopify app settings with the production URL
4. Use a production WSGI server (Gunicorn)
5. Use a proper database (PostgreSQL) instead of SQLite
6. Set up proper logging and monitoring

## Troubleshooting

### "Not authenticated" error
- Make sure you've completed the OAuth flow
- Check that your app credentials are correct
- Verify the redirect URL matches your app settings

### Scraping not working
- Check the job details page for specific error messages
- Verify your CSV has the correct columns
- Ensure vendor names match exactly (case-insensitive)

### Port already in use
- Change the port in `app.py` (last line)
- Or use: `python app.py --port 5001`
