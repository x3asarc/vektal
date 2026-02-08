"""Configuration loading and validation for vendor configs and store profiles."""

from .vendor_schema import VendorConfig, SKUPattern, VendorURLs, ScrapingConfig
from .store_profile_schema import StoreProfile, KnownVendor
from .loader import (
    load_vendor_config,
    load_store_profile,
    save_vendor_config,
    save_store_profile,
    list_vendor_configs
)

__all__ = [
    'VendorConfig',
    'SKUPattern',
    'VendorURLs',
    'ScrapingConfig',
    'StoreProfile',
    'KnownVendor',
    'load_vendor_config',
    'load_store_profile',
    'save_vendor_config',
    'save_store_profile',
    'list_vendor_configs',
]
