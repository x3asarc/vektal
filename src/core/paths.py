"""Central path configuration for all file references."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Configuration
CONFIG_DIR = PROJECT_ROOT / "config"
VENDOR_CONFIGS_PATH = str(CONFIG_DIR / "vendor_configs.yaml")
PRODUCT_QUALITY_RULES_PATH = str(CONFIG_DIR / "product_quality_rules.yaml")

# Data
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = str(DATA_DIR / "scraper_app.db")
PUSH_PROOF_CSV = str(DATA_DIR / "output" / "push_proof.csv")
NOT_FOUND_CSV = str(DATA_DIR / "output" / "not_found.csv")
VISION_CACHE_DB = os.getenv("VISION_AI_CACHE_DB", str(DATA_DIR / "vision_cache.db"))
VISION_PROOF_CSV = str(DATA_DIR / "output" / "vision_proof.csv")

# Output
SCRAPED_IMAGES_DIR = str(PROJECT_ROOT / "scraped_images")

# Create directories if needed
(DATA_DIR / "input").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "output").mkdir(parents=True, exist_ok=True)
