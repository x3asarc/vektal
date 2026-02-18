"""
SKU/EAN Validation Utility

Distinguishes between SKUs and EAN/barcode numbers to prevent confusion.

Key Rules:
- EANs are 13-digit numeric codes (sometimes 8 or 12)
- SKUs are shorter alphanumeric codes (typically 5-10 characters)
- If a field contains a 13-digit number, it's an EAN, NOT a SKU
"""

import re


def is_ean(value: str) -> bool:
    """
    Check if a value is an EAN/barcode.

    EANs are:
    - Exactly 8, 12, or 13 digits
    - All numeric
    - No letters or special characters

    Args:
        value: The value to check

    Returns:
        True if the value is an EAN, False otherwise
    """
    if not value:
        return False

    value_str = str(value).strip()

    # EAN must be all digits
    if not value_str.isdigit():
        return False

    # EAN is typically 8, 12, or 13 digits
    # Most common is EAN-13 (13 digits)
    length = len(value_str)
    return length in (8, 12, 13)


def is_sku(value: str) -> bool:
    """
    Check if a value is a SKU.

    SKUs are:
    - Alphanumeric (letters and/or numbers)
    - Typically 5-10 characters
    - NOT 13-digit numbers (those are EANs)

    Args:
        value: The value to check

    Returns:
        True if the value is likely a SKU, False otherwise
    """
    if not value:
        return False

    value_str = str(value).strip()

    # If it's an EAN, it's NOT a SKU
    if is_ean(value_str):
        return False

    # SKU should be alphanumeric
    if not re.match(r'^[A-Za-z0-9_-]+$', value_str):
        return False

    # SKU is typically 5-10 characters (can be longer for some systems)
    length = len(value_str)
    return 3 <= length <= 15


def validate_sku_ean_fields(sku_value: str, barcode_value: str) -> dict:
    """
    Validate SKU and barcode fields and suggest corrections.

    Args:
        sku_value: Value in the SKU field
        barcode_value: Value in the barcode field

    Returns:
        Dict with:
            - has_issues: bool
            - issues: list of issue descriptions
            - suggested_sku: corrected SKU value
            - suggested_barcode: corrected barcode value
    """
    issues = []
    suggested_sku = sku_value
    suggested_barcode = barcode_value

    # Check if SKU field contains an EAN
    if sku_value and is_ean(sku_value):
        issues.append(f"SKU field contains EAN barcode ({sku_value}) - should be actual SKU")
        suggested_barcode = sku_value  # Move to barcode field
        suggested_sku = None  # Clear SKU, needs correct value

    # Check if barcode field contains a SKU
    if barcode_value and is_sku(barcode_value) and not is_ean(barcode_value):
        issues.append(f"Barcode field contains SKU ({barcode_value}) - should be EAN")

    # Check if both fields are the same and both are EAN
    if sku_value == barcode_value and is_ean(sku_value):
        issues.append(f"Both SKU and barcode fields contain same EAN ({sku_value}) - SKU is missing")
        suggested_barcode = sku_value
        suggested_sku = None

    return {
        "has_issues": len(issues) > 0,
        "issues": issues,
        "suggested_sku": suggested_sku,
        "suggested_barcode": suggested_barcode
    }


def format_sku_ean_info(sku_value: str, barcode_value: str) -> str:
    """
    Format SKU/EAN information for display.

    Args:
        sku_value: SKU value
        barcode_value: Barcode value

    Returns:
        Formatted string describing the SKU/EAN status
    """
    lines = []

    if sku_value:
        if is_ean(sku_value):
            lines.append(f"SKU: {sku_value} (WARNING: This is an EAN, not a SKU!)")
        else:
            lines.append(f"SKU: {sku_value} (OK)")

    if barcode_value:
        if is_ean(barcode_value):
            lines.append(f"Barcode: {barcode_value} (EAN-13, OK)")
        else:
            lines.append(f"Barcode: {barcode_value} (WARNING: Not a valid EAN)")

    if not sku_value:
        lines.append("SKU: (missing)")

    if not barcode_value:
        lines.append("Barcode: (missing)")

    return "\n".join(lines)


# Example usage and tests
if __name__ == "__main__":
    print("=== SKU/EAN Validation Tests ===\n")

    test_cases = [
        ("40070", "5996546033389"),  # Correct: SKU and EAN
        ("5996546033389", "5996546033389"),  # Wrong: EAN in SKU field
        ("20738", "5997412742664"),  # Correct: SKU and EAN
        ("5997412742664", ""),  # Wrong: EAN in SKU field, no barcode
        ("ABC123", "1234567890123"),  # Correct: alphanumeric SKU, EAN
    ]

    for sku, barcode in test_cases:
        print(f"Testing: SKU='{sku}', Barcode='{barcode}'")
        print(f"  is_ean(SKU): {is_ean(sku)}")
        print(f"  is_sku(SKU): {is_sku(sku)}")
        print(f"  is_ean(Barcode): {is_ean(barcode)}")

        validation = validate_sku_ean_fields(sku, barcode)
        if validation["has_issues"]:
            print(f"  ISSUES DETECTED:")
            for issue in validation["issues"]:
                print(f"    - {issue}")
            print(f"  Suggested SKU: {validation['suggested_sku']}")
            print(f"  Suggested Barcode: {validation['suggested_barcode']}")
        else:
            print(f"  OK")

        print()
