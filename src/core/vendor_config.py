"""
Vendor Configuration Management System
Handles loading and applying vendor-specific settings for image naming and alt text
"""

import os
import re
import yaml
from typing import Dict, Optional, Any


class VendorConfigManager:
    """
    Manages vendor-specific configurations for image processing.

    Loads vendor settings from vendor_configs.yaml and provides
    methods to apply vendor-specific patterns for filenames and alt text.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the vendor configuration manager.

        Args:
            config_path: Path to the YAML configuration file
        """
        if config_path is None:
            from src.core.paths import VENDOR_CONFIGS_PATH
            config_path = VENDOR_CONFIGS_PATH
        self.config_path = config_path
        self.configs = {}
        self.category_keywords = {}
        self.load_config()

    def load_config(self):
        """Load vendor configurations from YAML file."""
        if not os.path.exists(self.config_path):
            print(f"Warning: Vendor config file not found: {self.config_path}")
            print("Using default configuration only.")
            self.configs = {"default": self._get_default_config()}
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Separate category keywords from vendor configs
            self.category_keywords = data.pop('category_keywords', {})
            self.configs = data

            print(f"Loaded configurations for {len(self.configs)} vendors")

        except Exception as e:
            print(f"Error loading vendor config: {e}")
            print("Using default configuration only.")
            self.configs = {"default": self._get_default_config()}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when config file is missing."""
        return {
            "country_of_origin": "SI",
            "filename_pattern": "{product_name}_{sku}",
            "alt_text_template": "{product_name}",
            "hs_code_default": "9999.00",
            "keyword_categories": {"default": []},
            "scraper": {"enabled": False}
        }

    def detect_vendor(self, vendor_name: Optional[str]) -> str:
        """
        Detect and normalize vendor name.

        Args:
            vendor_name: Vendor name from product data

        Returns:
            Normalized vendor key (lowercase) or 'default' if not found
        """
        if not vendor_name:
            return "default"

        # Normalize vendor name (lowercase, strip whitespace)
        normalized = str(vendor_name).lower().strip()

        # Direct match
        if normalized in self.configs:
            return normalized

        # Partial match (e.g., "Pentart Hungary" matches "pentart")
        for vendor_key in self.configs.keys():
            if vendor_key != "default" and vendor_key in normalized:
                return vendor_key

        # No match - use default
        return "default"

    def get_vendor_config(self, vendor_name: Optional[str]) -> Dict[str, Any]:
        """
        Get configuration for a specific vendor.

        Args:
            vendor_name: Vendor name from product data

        Returns:
            Vendor configuration dictionary
        """
        vendor_key = self.detect_vendor(vendor_name)
        config = self.configs.get(vendor_key, self.configs.get("default"))

        # Add vendor key to config for reference
        config["_vendor_key"] = vendor_key

        return config

    def detect_category(self, product_title: str, vendor_name: Optional[str] = None) -> Optional[str]:
        """
        Auto-detect product category from title.

        Args:
            product_title: Product title/description
            vendor_name: Optional vendor name for vendor-specific category detection

        Returns:
            Detected category key or None
        """
        if not product_title:
            return None

        title_lower = product_title.lower()

        # Check category keywords (multi-language)
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    return category

        return None

    def get_hs_code(self, product_title: str, vendor_name: Optional[str] = None) -> str:
        """
        Get HS code for a product based on title and vendor.

        Args:
            product_title: Product title/description
            vendor_name: Vendor name

        Returns:
            HS code string
        """
        vendor_config = self.get_vendor_config(vendor_name)

        # Detect category
        category = self.detect_category(product_title, vendor_name)

        # Get HS code from vendor's category mapping
        if category and "hs_code_map" in vendor_config:
            hs_code = vendor_config["hs_code_map"].get(category)
            if hs_code:
                return hs_code

        # Fall back to vendor default
        return vendor_config.get("hs_code_default", "9999.00")

    def get_keywords_for_category(self, category: str, vendor_name: Optional[str] = None) -> list:
        """
        Get SEO keywords for a product category.

        Args:
            category: Product category
            vendor_name: Vendor name

        Returns:
            List of keyword strings
        """
        if not category:
            return []

        vendor_config = self.get_vendor_config(vendor_name)
        keyword_categories = vendor_config.get("keyword_categories", {})

        return keyword_categories.get(category, [])

    def generate_filename(self, product_name: str, sku: str, vendor_name: Optional[str] = None,
                         category: Optional[str] = None, extension: str = ".jpg") -> str:
        """
        Generate vendor-specific filename using configured pattern.

        Args:
            product_name: Cleaned product name
            sku: Product SKU
            vendor_name: Vendor name
            category: Product category (auto-detected if None)
            extension: File extension (default .jpg)

        Returns:
            Generated filename with extension
        """
        from image_scraper import get_valid_filename

        vendor_config = self.get_vendor_config(vendor_name)
        vendor_key = vendor_config.get("_vendor_key", "default")

        # Auto-detect category if not provided
        if not category:
            category = self.detect_category(product_name, vendor_name)

        # Get filename pattern
        pattern = vendor_config.get("filename_pattern", "{product_name}_{sku}")

        # Prepare template variables
        variables = {
            "product_name": get_valid_filename(product_name),
            "sku": get_valid_filename(sku),
            "category": get_valid_filename(category) if category else "product",
            "vendor": vendor_key,
            "country": vendor_config.get("country_of_origin", "SI").lower()
        }

        # Apply template
        try:
            filename_base = pattern.format(**variables)
        except KeyError as e:
            print(f"Warning: Invalid template variable in filename_pattern: {e}")
            filename_base = f"{variables['product_name']}_{variables['sku']}"

        # Ensure extension starts with dot
        if not extension.startswith('.'):
            extension = '.' + extension

        return filename_base + extension

    def generate_alt_text(self, product_name: str, vendor_name: Optional[str] = None,
                         category: Optional[str] = None, add_keywords: bool = False) -> str:
        """
        Generate vendor-specific alt text using configured template.

        Args:
            product_name: Cleaned product name
            vendor_name: Vendor name
            category: Product category (auto-detected if None)
            add_keywords: Whether to inject SEO keywords

        Returns:
            Generated alt text
        """
        from image_scraper import clean_product_name, validate_alt_text

        vendor_config = self.get_vendor_config(vendor_name)
        vendor_key = vendor_config.get("_vendor_key", "default")

        # Clean product name first
        product_name = clean_product_name(product_name) or product_name

        # Auto-detect category if not provided
        if not category:
            category = self.detect_category(product_name, vendor_name)

        # Get alt text template
        template = vendor_config.get("alt_text_template", "{product_name}")

        # Prepare template variables
        variables = {
            "product_name": product_name,
            "category": category if category else "",
            "vendor": vendor_key.title(),
            "country": vendor_config.get("country_of_origin", "SI")
        }

        # Apply template
        try:
            alt_text = template.format(**variables)
        except KeyError as e:
            print(f"Warning: Invalid template variable in alt_text_template: {e}")
            alt_text = product_name

        # Inject keywords if requested
        if add_keywords and category:
            keywords = self.get_keywords_for_category(category, vendor_name)
            if keywords and len(keywords) > 0:
                # Add first keyword if not already present
                keyword = keywords[0]
                if keyword.lower() not in alt_text.lower():
                    alt_text = f"{alt_text} - {keyword}"

        # Validate and clean
        alt_text, warning = validate_alt_text(alt_text)
        if warning:
            print(f"  Alt text validation: {warning}")

        return alt_text

    def get_country_of_origin(self, vendor_name: Optional[str] = None) -> str:
        """
        Get country of origin for a vendor.

        Args:
            vendor_name: Vendor name

        Returns:
            2-letter country code
        """
        vendor_config = self.get_vendor_config(vendor_name)
        return vendor_config.get("country_of_origin", "SI")

    def is_scraper_enabled(self, vendor_name: Optional[str] = None) -> bool:
        """
        Check if scraper is enabled for a vendor.

        Args:
            vendor_name: Vendor name

        Returns:
            True if scraper is enabled, False otherwise
        """
        vendor_config = self.get_vendor_config(vendor_name)
        scraper_config = vendor_config.get("scraper", {})
        return scraper_config.get("enabled", False)

    def get_scraper_config(self, vendor_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get scraper configuration for a vendor.

        Args:
            vendor_name: Vendor name

        Returns:
            Scraper configuration dictionary
        """
        vendor_config = self.get_vendor_config(vendor_name)
        return vendor_config.get("scraper", {})


# Global instance (singleton pattern)
_vendor_manager = None


def get_vendor_manager(reload: bool = False) -> VendorConfigManager:
    """
    Get the global VendorConfigManager instance.

    Args:
        reload: If True, reload configuration from file

    Returns:
        VendorConfigManager instance
    """
    global _vendor_manager

    if _vendor_manager is None or reload:
        _vendor_manager = VendorConfigManager()

    return _vendor_manager


# Convenience functions for backward compatibility
def get_vendor_config(vendor_name: Optional[str] = None) -> Dict[str, Any]:
    """Get configuration for a vendor."""
    return get_vendor_manager().get_vendor_config(vendor_name)


def generate_vendor_filename(product_name: str, sku: str, vendor_name: Optional[str] = None,
                            category: Optional[str] = None, extension: str = ".jpg") -> str:
    """Generate vendor-specific filename."""
    return get_vendor_manager().generate_filename(product_name, sku, vendor_name, category, extension)


def generate_vendor_alt_text(product_name: str, vendor_name: Optional[str] = None,
                            category: Optional[str] = None, add_keywords: bool = False) -> str:
    """Generate vendor-specific alt text."""
    return get_vendor_manager().generate_alt_text(product_name, vendor_name, category, add_keywords)


def get_vendor_hs_code(product_title: str, vendor_name: Optional[str] = None) -> str:
    """Get HS code for a product."""
    return get_vendor_manager().get_hs_code(product_title, vendor_name)


def get_vendor_country(vendor_name: Optional[str] = None) -> str:
    """Get country of origin for a vendor."""
    return get_vendor_manager().get_country_of_origin(vendor_name)


if __name__ == "__main__":
    # Test the vendor configuration system
    print("="*60)
    print("Vendor Configuration System - Test")
    print("="*60)

    manager = get_vendor_manager()

    # Test vendor detection
    print("\nVendor Detection:")
    test_vendors = ["Pentart", "AISTCRAFT", "Ciao Bella Italy", "Unknown Vendor", None]
    for vendor in test_vendors:
        detected = manager.detect_vendor(vendor)
        print(f"  '{vendor}' -> '{detected}'")

    # Test category detection
    print("\nCategory Detection:")
    test_titles = [
        "Pentart Acrylic Paint Red",
        "Rice Paper with Flowers",
        "Decorative Napkin Vintage",
        "Canvas 30x40cm",
        "Unknown Product"
    ]
    for title in test_titles:
        category = manager.detect_category(title)
        print(f"  '{title}' -> '{category}'")

    # Test filename generation
    print("\nFilename Generation:")
    test_cases = [
        ("Pentart Acrylic Paint Red", "R0530", "Pentart"),
        ("Rice Paper Flowers", "TAG123", "Aistcraft"),
        ("Decorative Napkin", "CB456", "Ciao Bella"),
    ]
    for product, sku, vendor in test_cases:
        filename = manager.generate_filename(product, sku, vendor)
        print(f"  {vendor}: '{product}' -> '{filename}'")

    # Test alt text generation
    print("\nAlt Text Generation:")
    for product, sku, vendor in test_cases:
        alt_text = manager.generate_alt_text(product, vendor)
        print(f"  {vendor}: '{product}' -> '{alt_text}'")

    # Test HS code lookup
    print("\nHS Code Lookup:")
    for product, sku, vendor in test_cases:
        hs_code = manager.get_hs_code(product, vendor)
        category = manager.detect_category(product)
        print(f"  {vendor} - {category}: '{product}' -> '{hs_code}'")

    print("\n" + "="*60)
    print("Test complete!")
