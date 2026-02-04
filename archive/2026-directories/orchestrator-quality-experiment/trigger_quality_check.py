"""
Helper function to trigger quality check from other scripts.

Usage in your scripts:
    from orchestrator.trigger_quality_check import trigger_quality_check

    # After updating a product
    trigger_quality_check(sku="ABC123", trigger="image_scrape", auto_repair=True)
"""

import os
import sys
import subprocess


def trigger_quality_check(sku, trigger=None, auto_repair=False):
    """
    Trigger quality check for a product.

    Args:
        sku: Product SKU
        trigger: Event that triggered this (e.g., "seo_update", "image_scrape")
        auto_repair: If True, automatically dispatch repair jobs

    Returns:
        bool: True if successful
    """
    script_path = os.path.join(
        os.path.dirname(__file__),
        "product_quality_agent.py"
    )

    python_exe = "./venv/Scripts/python.exe" if os.path.exists("./venv/Scripts/python.exe") else "python"

    cmd = [python_exe, script_path, "--sku", sku]

    if trigger:
        cmd.extend(["--trigger", trigger])

    if auto_repair:
        cmd.append("--auto-repair")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        return result.returncode == 0
    except Exception as e:
        print(f"[WARNING] Quality check failed: {e}")
        return False


# Example integration functions for specific scripts

def after_image_scrape(sku):
    """Call this after image_scraper.py completes."""
    print(f"\n[QUALITY CHECK] Triggering after image scrape...")
    return trigger_quality_check(sku, trigger="image_scrape", auto_repair=True)


def after_seo_update(sku):
    """Call this after SEO content generation."""
    print(f"\n[QUALITY CHECK] Triggering after SEO update...")
    return trigger_quality_check(sku, trigger="seo_update", auto_repair=True)


def after_barcode_found(sku):
    """Call this after barcode is found and updated."""
    print(f"\n[QUALITY CHECK] Triggering after barcode update...")
    return trigger_quality_check(sku, trigger="barcode_update", auto_repair=True)


def after_bulk_import(sku):
    """Call this after product import/creation."""
    print(f"\n[QUALITY CHECK] Triggering after product creation...")
    return trigger_quality_check(sku, trigger="product_created", auto_repair=True)
