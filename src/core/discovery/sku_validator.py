"""
SKU Validation Utilities

Validate, normalize, and extract information from SKUs.
Based on patterns from CONTEXT.md and quickcleanup/ implementation.
"""

import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class SKUInfo:
    """Information extracted from SKU."""
    original: str
    normalized: str
    base_sku: str  # Without size suffix
    size_suffix: Optional[str]  # L, S, M, etc.
    product_line: Optional[str]  # R, RP, P, AC, etc.
    is_valid: bool
    validation_errors: list[str]


def normalize_sku(sku: str) -> str:
    """
    Normalize SKU to canonical format.

    - Strips whitespace
    - Converts to uppercase
    - Removes common separators (-, _)
    - Removes leading/trailing special characters

    Args:
        sku: Raw SKU string

    Returns:
        Normalized SKU string
    """
    if not sku:
        return ""

    # Strip whitespace
    normalized = sku.strip()

    # Convert to uppercase
    normalized = normalized.upper()

    # Remove common separators (but keep structure)
    # Don't remove hyphens that are part of the format (e.g., P-12345)
    normalized = normalized.replace(" ", "")
    normalized = normalized.replace("_", "")

    # Remove leading/trailing special characters
    normalized = re.sub(r'^[^A-Z0-9]+', '', normalized)
    normalized = re.sub(r'[^A-Z0-9]+$', '', normalized)

    return normalized


def validate_sku(
    sku: str,
    min_length: int = 3,
    max_length: int = 20
) -> tuple[bool, list[str]]:
    """
    Validate SKU format.

    Args:
        sku: SKU to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    if not sku:
        return False, ["SKU is empty"]

    normalized = normalize_sku(sku)

    if len(normalized) < min_length:
        errors.append(f"SKU too short (min {min_length} characters)")

    if len(normalized) > max_length:
        errors.append(f"SKU too long (max {max_length} characters)")

    # Must contain at least one letter or digit
    if not re.search(r'[A-Z0-9]', normalized):
        errors.append("SKU must contain letters or digits")

    # Check for suspicious patterns
    if normalized.startswith('0' * 5):
        errors.append("SKU looks like a placeholder (all zeros)")

    if normalized.lower() in ['test', 'sample', 'demo', 'xxx', 'tbd']:
        errors.append("SKU appears to be a placeholder")

    return len(errors) == 0, errors


def extract_sku_info(sku: str) -> SKUInfo:
    """
    Extract structured information from SKU.

    Handles patterns like:
    - R0530 (ITD Collection - no suffix = A4)
    - R0530L (ITD Collection - L suffix = A3)
    - P-12345 (Pentart format)
    - AC1234 (Aisticraft format)

    Args:
        sku: SKU to analyze

    Returns:
        SKUInfo with extracted components
    """
    normalized = normalize_sku(sku)
    is_valid, errors = validate_sku(normalized)

    # Detect size suffix (common patterns)
    size_suffix = None
    base_sku = normalized

    # Check for trailing size indicators
    size_suffix_patterns = [
        (r'([A-Z0-9]+)(L)$', 'L'),      # L = Large (A3)
        (r'([A-Z0-9]+)(XL)$', 'XL'),    # XL = Extra Large (A2)
        (r'([A-Z0-9]+)(S)$', 'S'),      # S = Small (A5)
        (r'([A-Z0-9]+)(M)$', 'M'),      # M = Medium (A4)
    ]

    for pattern, suffix in size_suffix_patterns:
        match = re.match(pattern, normalized)
        if match:
            base_sku = match.group(1)
            size_suffix = suffix
            break

    # Extract product line prefix
    product_line = None
    prefix_patterns = [
        r'^(R)(\d+)',       # R = ITD rice paper
        r'^(RP)(\d+)',      # RP = ITD rice paper premium
        r'^(P)[-]?(\d+)',   # P = Pentart
        r'^(AC)(\d+)',      # AC = Aisticraft
        r'^(FN)(\d+)',      # FN = FN Deco
        r'^(PD)(\d+)',      # PD = Paper Designs
    ]

    for pattern in prefix_patterns:
        match = re.match(pattern, normalized, re.IGNORECASE)
        if match:
            product_line = match.group(1).upper()
            break

    return SKUInfo(
        original=sku,
        normalized=normalized,
        base_sku=base_sku,
        size_suffix=size_suffix,
        product_line=product_line,
        is_valid=is_valid,
        validation_errors=errors
    )


def sku_matches_pattern(sku: str, pattern: str) -> bool:
    """
    Check if SKU matches a regex pattern.

    Args:
        sku: SKU to check
        pattern: Regex pattern string

    Returns:
        True if SKU matches pattern
    """
    normalized = normalize_sku(sku)
    try:
        return bool(re.match(pattern, normalized, re.IGNORECASE))
    except re.error:
        return False


def infer_size_from_sku(sku: str, size_mappings: dict[str, str] = None) -> str:
    """
    Infer size from SKU suffix.

    Args:
        sku: SKU to analyze
        size_mappings: Dict mapping suffixes to sizes (default: ITD-style)

    Returns:
        Inferred size (e.g., "A4", "A3")
    """
    if size_mappings is None:
        size_mappings = {
            "": "A4",    # No suffix = A4 (default)
            "L": "A3",   # L = Large = A3
            "XL": "A2",  # XL = Extra Large = A2
            "S": "A5",   # S = Small = A5
            "M": "A4",   # M = Medium = A4
        }

    info = extract_sku_info(sku)
    suffix = info.size_suffix or ""

    return size_mappings.get(suffix, size_mappings.get("", "A4"))
