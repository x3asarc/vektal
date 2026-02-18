"""
Demo script showing Image Processing Framework in action

Demonstrates all framework features:
- Hybrid naming (AI + SEO)
- Transformation rules
- Upload strategy selection
- Positioning logic
- Vendor overrides
"""

from src.core.image_framework import get_framework


def demo_primary_image():
    """Demo: Processing a primary image"""
    print("=" * 70)
    print("DEMO 1: Primary Image Processing")
    print("=" * 70)

    framework = get_framework()

    product = {
        "id": "gid://shopify/Product/9876543210",
        "title": "Galaxy Flakes 15g - Jupiter white",
        "vendor": "Pentart"
    }

    image_url = "https://cdn.shopify.com/s/files/1/0123/4567/files/jupiter-white.jpg"

    result = framework.process_image(
        product=product,
        image_url=image_url,
        image_role="primary",
        vendor="Pentart"
    )

    print(f"\nProduct: {product['title']}")
    print(f"Vendor: {product['vendor']}")
    print(f"Image URL: {image_url}")
    print(f"\nOK Framework Results:")
    print(f"   Filename: {result['filename']}")
    print(f"   Alt Text: {result['alt_text']}")
    print(f"   Image Type: {result['image_type']}")
    print(f"   Upload Strategy: {result['upload_strategy']}")
    print(f"   Position: {result['position']}")
    print(f"   Format: {result['transformations']['format']}")
    print(f"   Square Size: {result['transformations']['convert_to_square']['target_size']}px")


def demo_shared_image():
    """Demo: Processing a shared image"""
    print("\n" + "=" * 70)
    print("DEMO 2: Shared Image Processing")
    print("=" * 70)

    framework = get_framework()

    product = {
        "id": "gid://shopify/Product/9876543210",
        "title": "Galaxy Flakes 15g - Jupiter white",
        "vendor": "Pentart"
    }

    image_url = "https://cdn.shopify.com/s/files/1/0123/4567/files/groupshot.jpg"

    result = framework.process_image(
        product=product,
        image_url=image_url,
        image_role="shared",  # Shared image (applied to all variants)
        vendor="Pentart"
    )

    print(f"\nProduct: {product['title']}")
    print(f"Vendor: {product['vendor']}")
    print(f"Image URL: {image_url}")
    print(f"Image Role: shared (applied to all variants)")
    print(f"\nOK Framework Results:")
    print(f"   Filename: {result['filename']}")
    print(f"   Alt Text: {result['alt_text']}")
    print(f"   Image Type: {result['image_type']}")
    print(f"   Upload Strategy: {result['upload_strategy']}")
    print(f"   Position: {result['position']}")
    print(f"   Format: {result['transformations']['format']}")
    print(f"\nNote: Note: Same filename will be used for ALL variants")


def demo_filename_validation():
    """Demo: Filename validation"""
    print("\n" + "=" * 70)
    print("DEMO 3: Filename Validation")
    print("=" * 70)

    framework = get_framework()

    test_filenames = [
        "pentart-galaxy-flakes-15g-packshot.jpg",  # Valid
        "pentart-galaxy-flakes-15g-jupiter-white.png",  # Valid
        "PENTART-Galaxy-Flakes.JPG",  # Invalid (uppercase)
        "product name with spaces.jpg",  # Invalid (spaces)
        "product!@#special$%^chars.png",  # Invalid (special chars)
    ]

    print("\nFilename Validation Results:")
    for filename in test_filenames:
        is_valid = framework.validate_filename(filename)
        status = "OK VALID" if is_valid else "INVALID INVALID"
        print(f"   {status}: {filename}")


def demo_transformation_rules():
    """Demo: Transformation rules"""
    print("\n" + "=" * 70)
    print("DEMO 4: Transformation Rules")
    print("=" * 70)

    framework = get_framework()

    # Primary image transformations
    print("\nImage:  Primary Image (Packshot):")
    transformations_primary = framework.processor.get_transformations(
        image_type="packshot",
        image_role="primary",
        vendor="Pentart"
    )
    print(f"   Format: {transformations_primary['format']}")
    print(f"   Square Method: {transformations_primary['convert_to_square']['method']}")
    print(f"   Target Size: {transformations_primary['convert_to_square']['target_size']}px")
    print(f"   Transparency: {transformations_primary['ensure_transparency']['convert_to_rgba']}")

    # Shared image transformations
    print("\nImage:  Shared Image (Groupshot):")
    transformations_shared = framework.processor.get_transformations(
        image_type="groupshot",
        image_role="shared",
        vendor="Pentart"
    )
    print(f"   Format: {transformations_shared['format']}")
    print(f"   Square Method: {transformations_shared['convert_to_square']['method']}")
    print(f"   Target Size: {transformations_shared['convert_to_square']['target_size']}px")
    print(f"   Quality: {transformations_shared['format_config'].get('quality', 'N/A')}")


def demo_naming_patterns():
    """Demo: Naming patterns"""
    print("\n" + "=" * 70)
    print("DEMO 5: Naming Patterns")
    print("=" * 70)

    framework = get_framework()

    product_context_primary = {
        "product_slug": "galaxy-flakes-15g",
        "variant_slug": "jupiter-white",
        "product_line": "Galaxy Flakes 15g",
        "variant_name": "Jupiter white",
        "vendor": "Pentart",
        "role": "primary"
    }

    product_context_shared = {
        "product_slug": "galaxy-flakes-15g",
        "product_line": "Galaxy Flakes",
        "vendor": "Pentart",
        "role": "shared"
    }

    print("\nFiles: Primary Image Filenames:")
    for image_type in ["packshot", "detail", "lifestyle"]:
        filename = framework.naming_engine.generate_filename(
            image_type=image_type,
            product_context=product_context_primary,
            image_role="primary",
            vendor="pentart"
        )
        print(f"   {image_type}: {filename}")

    print("\nFiles: Shared Image Filenames:")
    for image_type in ["packshot", "groupshot", "detail", "lifestyle"]:
        filename = framework.naming_engine.generate_filename(
            image_type=image_type,
            product_context=product_context_shared,
            image_role="shared",
            vendor="pentart"
        )
        print(f"   {image_type}: {filename}")

    print("\nText: Alt Text Examples:")
    for image_type in ["packshot", "groupshot"]:
        role = "primary" if image_type == "packshot" else "shared"
        context = product_context_primary if role == "primary" else product_context_shared
        alt_text = framework.naming_engine.generate_alt_text(
            image_type=image_type,
            product_context=context,
            image_role=role,
            vendor="Pentart"
        )
        print(f"   {image_type} ({role}): {alt_text}")


def main():
    """Run all demos"""
    print("\n")
    print("+" + "=" * 68 + "+")
    print("|" + " " * 15 + "IMAGE PROCESSING FRAMEWORK DEMO" + " " * 22 + "|")
    print("+" + "=" * 68 + "+")

    try:
        demo_primary_image()
        demo_shared_image()
        demo_filename_validation()
        demo_transformation_rules()
        demo_naming_patterns()

        print("\n" + "=" * 70)
        print("OK ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nFramework Features Demonstrated:")
        print("  * Hybrid naming (AI type + SEO structure)")
        print("  * Automatic transformation rules")
        print("  * Upload strategy selection")
        print("  * Positioning logic (primary vs shared)")
        print("  * Filename validation")
        print("  * German alt text generation")
        print("  * Format optimization (PNG/JPG)")
        print("\nDocs: See docs/IMAGE_PROCESSING_FRAMEWORK.md for full documentation")
        print()

    except Exception as e:
        print(f"\nINVALID ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
