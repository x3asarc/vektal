# Shopify Multi-Supplier Scraper App

A Shopify app that automatically syncs product images, prices, and details from multiple suppliers to your Shopify store.

## Features

- **Multi-Supplier Support**: Automatically scrapes from:
  - Aistcraft (SI)
  - Pentart (HU)
  - Ciao Bella (IT)
  - ITD Collection (PL)
  - Paper Designs (IT)
  - FN Deco (HU)

- **Automated Sync**: Uploads product images, updates costs, barcodes, country of origin, and HS codes
- **Web Interface**: Easy-to-use UI embedded in Shopify admin
- **Job Tracking**: Monitor scraping progress in real-time
- **Resume Capability**: Automatically skips already-processed products

## Setup Instructions

### 1. Create a Shopify App

1. Go to [Shopify Partners Dashboard](https://partners.shopify.com/)
2. Create a new app
3. Set the app URL to: `https://your-domain.com` (or `http://localhost:5000` for development)
4. Set redirect URL to: `https://your-domain.com/auth/callback`
5. Note your **API Key** and **API Secret**

### 2. Configure Environment Variables

Create or update your `.env` file:

```env
# Shopify App Credentials (from Partners Dashboard)
SHOPIFY_API_KEY=your_api_key_here
SHOPIFY_API_SECRET=your_api_secret_here

# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here
APP_URL=http://localhost:5000

# API Version
API_VERSION=2024-01
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the App

```bash
python app.py
```

The app will be available at `http://localhost:5000`

### 5. Install the App in Your Shopify Store

1. Visit: `http://localhost:5000/auth/shopify?shop=your-store.myshopify.com`
2. Authorize the app
3. You'll be redirected to the app interface

## Usage

1. **Upload CSV**: Click "Select File" or drag and drop a CSV file
2. **CSV Format**: Your CSV must have these columns:
   - `Handle`: Product handle in Shopify
   - `SKU`: Product SKU
   - `Vendor`: Supplier name (Aistcraft, Pentart, Ciao Bella, ITD Collection, Paper Designs, FN Deco)

3. **Monitor Progress**: View job status and results in real-time
4. **View Details**: Click "View" on any job to see detailed results

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
python app.py
```

### Testing with ngrok (for local development)

1. Install ngrok: `https://ngrok.com/`
2. Run: `ngrok http 5000`
3. Update `APP_URL` in `.env` to your ngrok URL
4. Update your Shopify app settings with the ngrok URL

## Production Deployment

For production, consider:

1. **Use a production WSGI server** (e.g., Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Use a proper database** (PostgreSQL instead of SQLite)

3. **Store access tokens securely** (database instead of session)

4. **Set up proper logging**

5. **Use environment variables** for all secrets

## API Endpoints

- `GET /` - Main app interface
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/<id>` - Get job details
- `POST /api/jobs` - Create new job (upload CSV)
- `POST /api/jobs/<id>/cancel` - Cancel a job
- `GET /auth/shopify` - Initiate OAuth
- `GET /auth/callback` - OAuth callback

## File Structure

```
.
├── app.py                 # Flask backend
├── image_scraper.py       # Scraping logic (existing)
├── templates/
│   ├── index.html        # Main app UI
│   └── job_detail.html   # Job details page
├── uploads/              # Uploaded CSV files
├── scraper_app.db        # SQLite database
└── requirements.txt      # Python dependencies
```

## Troubleshooting

### Authentication Issues
- Make sure your Shopify app credentials are correct
- Verify the redirect URL matches your app settings
- Check that your app has the required scopes

### Scraping Not Working
- Verify your CSV has the correct columns
- Check that vendor names match exactly
- Review job details for error messages

### Database Issues
- Delete `scraper_app.db` to reset (will lose all job history)

## Support

For issues or questions, check the job details page for specific error messages.
