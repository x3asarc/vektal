"""
Test script for image name rewriting and alt text improvements
Run this to verify the implementations are working correctly
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.image_scraper import clean_product_name, get_valid_filename, validate_alt_text


def test_clean_product_name():
    """Test clean_product_name() function"""
    print("\n" + "="*60)
    print("TEST 1: clean_product_name()")
    print("="*60)

    test_cases = [
        ("Product_8a4d9e6f-1234-5678-9012-abcdef123456", "Product"),
        ("Paint (HS code 3210)", "Paint"),
        ("Pentart Acrylic Paint R0530", "Pentart Acrylic Paint"),
        ("Rice Paper HS: 48021000", "Rice Paper"),
        ("Product TAG123", "Product"),
        ("Normal   Spaces", "Normal Spaces"),
        (None, None),
    ]

    passed = 0
    failed = 0

    for input_val, expected in test_cases:
        result = clean_product_name(input_val)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} | Input: '{input_val}' | Expected: '{expected}' | Got: '{result}'")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_get_valid_filename():
    """Test get_valid_filename() function"""
    print("\n" + "="*60)
    print("TEST 2: get_valid_filename()")
    print("="*60)

    test_cases = [
        ("Pentart Acrylic Paint", "pentart_acrylic_paint"),
        ("Product!!! With @@@ Special ###", "product_with_special"),
        ("UPPERCASE", "uppercase"),
        ("Multiple   Spaces", "multiple_spaces"),
        ("a" * 250, "a" * 200),  # Test length limiting
    ]

    passed = 0
    failed = 0

    for input_val, expected_pattern in test_cases:
        result = get_valid_filename(input_val)

        # For length test, just check length is <= 200
        if len(input_val) > 200:
            is_valid = len(result) <= 200
            status = "✅ PASS" if is_valid else "❌ FAIL"
        else:
            is_valid = result == expected_pattern
            status = "✅ PASS" if is_valid else "❌ FAIL"

        if is_valid:
            passed += 1
        else:
            failed += 1

        if len(input_val) > 50:
            print(f"{status} | Input: [long string] | Length check: {len(result)} <= 200")
        else:
            print(f"{status} | Input: '{input_val}' | Expected: '{expected_pattern}' | Got: '{result}'")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_validate_alt_text():
    """Test validate_alt_text() function"""
    print("\n" + "="*60)
    print("TEST 3: validate_alt_text()")
    print("="*60)

    test_cases = [
        ("Image of a product", "a product", True),  # Should remove "Image of"
        ("Picture of flowers", "flowers", True),  # Should remove "Picture of"
        ("Valid alt text", "Valid alt text", False),  # Should keep as is
        ("a" * 600, 512, True),  # Should truncate to max length
        ("", "", True),  # Should return empty with warning
    ]

    passed = 0
    failed = 0

    for i, (input_val, expected_check, should_warn) in enumerate(test_cases):
        result, warning = validate_alt_text(input_val)

        if i < 2:  # First two tests check content removal
            is_valid = result == expected_check
        elif i == 3:  # Length truncation test
            is_valid = len(result) <= expected_check
        elif i == 4:  # Empty string test
            is_valid = result == expected_check and warning is not None
        else:
            is_valid = result == expected_check

        has_warning = warning is not None
        status = "✅ PASS" if is_valid else "❌ FAIL"

        if is_valid:
            passed += 1
        else:
            failed += 1

        if len(input_val) > 50:
            print(f"{status} | Input: [long string] | Length: {len(result)} | Warning: {has_warning}")
        else:
            print(f"{status} | Input: '{input_val}' | Result: '{result}' | Warning: {'Yes' if has_warning else 'No'}")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_shopify_client_exists():
    """Test that ShopifyClient class exists and has required methods"""
    print("\n" + "="*60)
    print("TEST 4: ShopifyClient Class")
    print("="*60)

    try:
        from image_scraper import ShopifyClient

        required_methods = [
            'authenticate',
            'execute_graphql',
            'get_product_by_sku',
            'check_product_has_image',
            'delete_product_media',
            'update_product_media',
            'rename_media_files',
            'update_product_variants'
        ]

        client = ShopifyClient()
        passed = 0
        failed = 0

        for method_name in required_methods:
            if hasattr(client, method_name) and callable(getattr(client, method_name)):
                print(f"✅ PASS | Method '{method_name}' exists")
                passed += 1
            else:
                print(f"❌ FAIL | Method '{method_name}' missing")
                failed += 1

        print(f"\nResults: {passed} passed, {failed} failed")
        return failed == 0

    except ImportError as e:
        print(f"❌ FAIL | Could not import ShopifyClient: {e}")
        return False


def test_app_imports():
    """Test that all imports required by app.py exist"""
    print("\n" + "="*60)
    print("TEST 5: app.py Required Imports")
    print("="*60)

    required_imports = [
        'scrape_product_info',
        'ShopifyClient',
        'load_processed_skus',
        'clean_sku',
        'DEFAULT_COUNTRY_OF_ORIGIN',
        'get_hs_code'
    ]

    passed = 0
    failed = 0

    for import_name in required_imports:
        try:
            exec(f"from image_scraper import {import_name}")
            print(f"✅ PASS | Import '{import_name}' successful")
            passed += 1
        except ImportError as e:
            print(f"❌ FAIL | Import '{import_name}' failed: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("IMAGE NAME REWRITING & ALT TEXT - TEST SUITE")
    print("="*60)

    all_passed = True

    # Run all tests
    test_results = [
        ("clean_product_name", test_clean_product_name()),
        ("get_valid_filename", test_get_valid_filename()),
        ("validate_alt_text", test_validate_alt_text()),
        ("ShopifyClient class", test_shopify_client_exists()),
        ("app.py imports", test_app_imports()),
    ]

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} | {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Implementation is working correctly.")
    else:
        print("⚠️ SOME TESTS FAILED. Please review the output above.")
    print("="*60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
