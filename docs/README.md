# Shopify Multi-Supplier Automation Suite

A comprehensive automation toolkit for Shopify stores that synchronizes product data from multiple European suppliers, generates SEO-optimized content using AI, and provides both CLI and web-based interfaces for efficient product management.

## Overview

This project automates the tedious process of managing product data across multiple suppliers in a Shopify store. It scrapes product information (images, prices, specifications) from supplier websites, updates Shopify products via GraphQL API, and generates SEO-optimized content using Google Gemini AI.

### Key Features

- **Multi-Supplier Product Scraping**: Automated data extraction from 6+ European suppliers
- **Shopify Integration**: Direct product updates via GraphQL API
- **AI-Powered SEO Generation**: Creates optimized meta titles, descriptions, and product content
- **Web Application**: Shopify-embedded app for easy job management
- **CLI Tools**: Command-line scripts for advanced automation
- **Resume Capability**: Track progress and skip already-processed products
- **Real-time Job Tracking**: Monitor scraping progress with detailed status updates

## Supported Suppliers

- **Aistcraft** (Slovenia) - Paper crafting supplies
- **Pentart** (Hungary) - Art and craft materials
- **Ciao Bella** (Italy) - Decorative papers and embellishments
- **ITD Collection** (Poland) - Decoupage and crafting supplies (includes EAN/HS code extraction)
- **Paper Designs** (Italy) - Specialty papers
- **FN Deco** (Hungary) - Decorative materials

## Architecture

### Components

1. **Core Scraping Engine** (`image_scraper.py`)
   - Multi-threaded web scraping with supplier-specific logic
   - Image download and upload to Shopify
   - Cost, barcode, HS code, and country of origin updates
   - Duplicate image cleanup

2. **Web Application** (`app.py`)
   - Flask-based Shopify embedded app
   - OAuth authentication
   - Job queue management
   - Real-time progress tracking
   - CSV upload interface

3. **SEO Content Generator** (`seo_generator.py`)
   - Google Gemini AI integration
   - German-language optimization
   - SEO validation (2026 best practices)
   - Batch processing with filters

4. **Specialized Update Scripts**
   - `pentart_manager.py` - Pentart-specific product updates
   - `find_and_update_by_barcode.py` - Barcode-based product matching
   - `quick_update_product.py` - Fast single-product updates
   - `update_sku.py` / `update_sku_rest.py` - SKU management

## Quick Start

### Prerequisites

- Python 3.8+
- Shopify store with API access
- Shopify Partner account (for web app)
- Google Gemini API key (for SEO features)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd "Shopify Scraping Script"
```

2. Create and activate virtual environment:
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
# Create .env file with your credentials
SHOPIFY_CLIENT_ID=your_shopify_client_id
SHOPIFY_CLIENT_SECRET=your_shopify_client_secret
SHOP_DOMAIN=your-store.myshopify.com
GEMINI_API_KEY=your_gemini_api_key  # For SEO features
API_VERSION=2024-01
```

### Running the Web App

1. Configure Shopify app (see [SETUP.md](SETUP.md) for detailed instructions)

2. Start the Flask server:
```bash
python app.py
```

3. Access at `http://localhost:5000` or install in your Shopify store:
```
http://localhost:5000/auth/shopify?shop=your-store.myshopify.com
```

### Running CLI Scripts

#### Basic Product Scraping

```bash
# Scrape and update products from CSV
python image_scraper.py --live --csv products.csv

# Test mode (no Shopify updates)
python image_scraper.py --csv products.csv
```

Your CSV must contain:
- `Handle` - Shopify product handle
- `SKU` - Product SKU
- `Vendor` - Supplier name (must match supported suppliers)

#### SEO Content Generation

```bash
# Windows
run_seo_generator.bat --vendor "Pentart" --limit 10

# Linux/Mac
./run_seo_generator.sh --vendor "Pentart" --limit 10

# Filter by SKU
python scripts\generate_seo_quick.py --sku "2493"

# Filter by title
python scripts\generate_seo_quick.py --title "Farbe" --limit 5
```

Results are exported to `data/seo_preview.csv` for review before applying.

#### Pentart-Specific Updates

```bash
# Update Pentart products from their logistics file
python pentart_manager.py
```

#### Quick Product Updates

```bash
# Update single product by SKU
python quick_update_product.py <sku>

# Find and update by barcode
python find_and_update_by_barcode.py <barcode>
```

## Usage Examples

### Web App Workflow

1. Prepare CSV file with product data
2. Upload via web interface
3. Monitor job progress in real-time
4. View detailed results and logs
5. Download success/failure reports

### CLI Workflow

1. Create product CSV or use existing data
2. Run scraper in test mode first:
   ```bash
   python image_scraper.py --csv products.csv
   ```
3. Review logs and adjust as needed
4. Run in live mode:
   ```bash
   python image_scraper.py --live --csv products.csv
   ```
5. Check `push_proof.csv` for processing status

### SEO Generation Workflow

1. Generate preview content:
   ```bash
   run_seo_generator.bat --vendor "Pentart" --limit 5
   ```
2. Review `data/seo_preview.csv`
3. Validate character counts and quality
4. Apply to Shopify (Phase 2 - coming soon)

## Project Structure

```
Shopify Scraping Script/
├── app.py                          # Flask web application
├── image_scraper.py                # Core scraping engine
├── seo_generator.py                # SEO content generator
├── pentart_manager.py              # Pentart-specific manager
├── ai_bot_server.py                # AI assistant server
├── bot_server.py                   # Legacy bot server
│
├── scripts/                        # Utility scripts
│   └── generate_seo_quick.py       # SEO CLI interface
│
├── utils/                          # Shared utilities
│   ├── seo_prompts.py              # Gemini prompt templates
│   └── seo_validator.py            # Content validation
│
├── web/                            # Web app frontend
│   ├── templates/                  # HTML templates
│   │   ├── index.html              # Main interface
│   │   └── job_detail.html         # Job details
│   └── app.js                      # Frontend JavaScript
│
├── data/                           # Data files
│   └── seo_preview.csv             # SEO generation output
│
├── uploads/                        # CSV uploads (web app)
├── results/                        # Scraping results
├── logs/                           # Application logs
├── archive/                        # Archived data
│
├── requirements.txt                # Python dependencies
├── .env                            # Environment configuration
│
├── README.md                       # This file
├── README_APP.md                   # Web app documentation
├── README_SEO_Generator.md         # SEO generator guide
├── SETUP.md                        # Detailed setup guide
├── PROJECT_SUMMARY.md              # Project status
├── IMPLEMENTATION_SUMMARY.md       # Technical implementation
├── PENTART_IMPLEMENTATION.md       # Pentart integration details
└── PRODUCT_REQUIREMENTS_DOCUMENT.md # Product requirements
```

## API Documentation

### Web App Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main app interface |
| `/api/jobs` | GET | List all jobs |
| `/api/jobs/<id>` | GET | Get job details |
| `/api/jobs` | POST | Create new job (upload CSV) |
| `/api/jobs/<id>/cancel` | POST | Cancel running job |
| `/auth/shopify` | GET | Initiate Shopify OAuth |
| `/auth/callback` | GET | OAuth callback handler |

### Shopify GraphQL Operations

The scraper uses Shopify GraphQL API for:
- Product queries (by SKU, handle, barcode)
- Image upload and management
- Inventory updates
- Metafield updates (cost, HS code, country of origin)
- Product variant updates

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SHOPIFY_CLIENT_ID` | Shopify app client ID | Yes |
| `SHOPIFY_CLIENT_SECRET` | Shopify app secret | Yes |
| `SHOP_DOMAIN` | Your Shopify store domain | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | For SEO |
| `API_VERSION` | Shopify API version | Yes |
| `FLASK_SECRET_KEY` | Flask session secret | For web app |
| `APP_URL` | App URL for OAuth | For web app |

### CSV Format

**Product Scraping CSV:**
```csv
Handle,SKU,Vendor
product-handle-1,SKU123,Pentart
product-handle-2,SKU456,Aistcraft
```

**Pentart Logistics CSV:**
Must include fields for SKU, price, stock, and other supplier-specific data.

## Features in Detail

### Intelligent Scraping

- **Supplier-Specific Logic**: Each supplier has custom scraping rules
- **Error Handling**: Retries, fallbacks, and detailed error logging
- **Rate Limiting**: Respects supplier rate limits to avoid blocking
- **User-Agent Rotation**: Mimics real browsers for protected sites
- **Image Optimization**: Downloads and validates images before upload

### Data Synchronization

- **Duplicate Prevention**: Checks existing data before updates
- **Incremental Updates**: Only updates changed fields
- **Resume Support**: Tracks processed products in `push_proof.csv`
- **Validation**: Ensures data integrity before Shopify updates
- **Rollback Safety**: Test mode prevents accidental changes

### SEO Optimization

- **AI-Powered**: Uses Google Gemini for natural, engaging content
- **German Language**: Optimized for German e-commerce market
- **Best Practices**: Follows 2026 SEO guidelines
  - Meta titles: 50-60 characters
  - Meta descriptions: 155-160 characters
  - Product descriptions: 300-500 words
- **Quality Validation**: Automatic checks for character limits and content quality

## Development

### Running in Development Mode

```bash
# Set Flask to development mode
export FLASK_ENV=development  # Linux/Mac
set FLASK_ENV=development     # Windows

python app.py
```

### Testing with ngrok

For local development with Shopify OAuth:

```bash
ngrok http 5000
```

Update `.env` with your ngrok URL:
```env
APP_URL=https://your-ngrok-url.ngrok.io
```

### Database

Web app uses SQLite (`scraper_app.db`) by default. For production:

1. Install PostgreSQL
2. Update database connection in `app.py`
3. Run migrations if needed

## Production Deployment

### Recommended Stack

- **Server**: Gunicorn WSGI server
- **Database**: PostgreSQL
- **Hosting**: Heroku, Railway, DigitalOcean, or similar
- **Logging**: Structured logging to file/service
- **Monitoring**: Health checks and error tracking

### Deployment Steps

1. Set production environment variables
2. Use production-grade database
3. Enable HTTPS for OAuth
4. Configure proper logging
5. Set up monitoring and alerts
6. Use Gunicorn instead of Flask dev server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

## Troubleshooting

### Common Issues

**Authentication Failed**
- Verify Shopify credentials in `.env`
- Check API scopes in Shopify Partner dashboard
- Ensure OAuth redirect URL matches app settings

**Scraping Not Working**
- Verify supplier name matches exactly
- Check internet connectivity
- Review logs for specific errors
- Some suppliers may have changed their website structure

**SEO Generator Errors**
- Confirm Gemini API key is valid
- Check API quota limits
- Verify model name (`gemini-2.5-flash`)

**Database Locked**
- Close other connections to SQLite
- Consider upgrading to PostgreSQL for multi-user access

**Unicode/Encoding Issues (Windows)**
- Script auto-detects and uses ASCII fallback
- Set console to UTF-8: `chcp 65001`

## Contributing

Contributions are welcome! Areas for improvement:

- Additional supplier integrations
- Enhanced error recovery
- Improved web UI
- Batch SEO updates (Phase 2)
- Multi-language support
- Advanced scheduling features

## License

[Specify your license here]

## Support

For issues, questions, or feature requests:

1. Check existing documentation (README files)
2. Review job details/logs for specific errors
3. Consult Shopify GraphQL documentation
4. Refer to supplier website for changes

## Changelog

### Version 1.0 (Current)
- Multi-supplier scraping engine
- Shopify GraphQL integration
- Web application with job tracking
- SEO content generator (read-only)
- Pentart logistics integration
- Resume capability
- Comprehensive error handling

### Roadmap
- SEO content live updates (Phase 2)
- Scheduled automation
- Enhanced web UI
- Additional supplier support
- Performance optimizations
- Advanced analytics

---

**Built with**: Python, Flask, BeautifulSoup, Pandas, Google Gemini AI, Shopify GraphQL API

**Maintained by**: [Your Name/Organization]

**Last Updated**: January 2026
