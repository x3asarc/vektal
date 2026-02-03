"""
Auto-fix images based on verification recommendations
Downloads, transforms, and re-uploads images
"""

import requests
from io import BytesIO
from PIL import Image
from src.core.image_scraper import ShopifyClient
from src.core.image_framework import get_framework
from src.core.image_verifier import verify_and_fix_product_image

# Products needing fixes
PRODUCTS = [
    {
        "product_id": "gid://shopify/Product/10563043885394",
        "sku": "40070",
        "barcode": "5996546033389",
        "title": "Resin Tint jade 20 ml",
        "vendor": "Pentart",
        "image_url": "https://cdn.shopify.com/s/files/1/0422/5397/5709/files/40070p_drawn_png.png"
    },
    {
        "product_id": "gid://shopify/Product/10563042935122",
        "sku": "20738",
        "barcode": "5997412742664",
        "title": "Dekofolie Bronze 14 x 14 cm, 5 Stuck/Packung",
        "vendor": "Pentart",
        "image_url": "https://cdn.shopify.com/s/files/1/0422/5397/5709/files/20738p_drawn_png.png"
    },
    {
        "product_id": "gid://shopify/Product/10563042378066",
        "sku": "13397",
        "barcode": "5997412709667",
        "title": "Textilkleber 80 ml",
        "vendor": "Pentart",
        "image_url": "https://cdn.shopify.com/s/files/1/0422/5397/5709/files/13397p_drawn_png.png"
    }
]

def download_image(url):
    """Download image from URL"""
    print(f"  Downloading: {url[:70]}...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content

def apply_squaring_transformation(image_data):
    """Apply center crop squaring transformation"""
    img = Image.open(BytesIO(image_data))
    original_size = img.size
    print(f"  Original size: {original_size[0]}x{original_size[1]}")

    # Apply center crop to square
    width, height = img.size
    min_dim = min(width, height)

    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim

    img = img.crop((left, top, right, bottom))

    # Resize to target size (900x900)
    target_size = 900
    img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)

    # Convert to RGBA for transparency
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Save to bytes
    output = BytesIO()
    img.save(output, format='PNG', optimize=True)
    transformed_data = output.getvalue()

    print(f"  Transformed size: {target_size}x{target_size}")
    print(f"  File size: {len(image_data)} -> {len(transformed_data)} bytes")

    return transformed_data

def upload_image_to_shopify(client, product_id, image_data, filename, alt_text):
    """Upload transformed image using staged upload"""
    print(f"  Creating staged upload...")

    # Create staged upload
    mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
        stagedUploadsCreate(input: $input) {
            stagedTargets {
                url
                resourceUrl
                parameters {
                    name
                    value
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    """

    variables = {
        "input": [{
            "resource": "IMAGE",
            "filename": filename,
            "mimeType": "image/png",
            "fileSize": str(len(image_data)),
            "httpMethod": "POST"
        }]
    }

    result = client.execute_graphql(mutation, variables)

    if not result or "data" not in result:
        print(f"  ERROR: Failed to create staged upload")
        return False

    staged_targets = result["data"]["stagedUploadsCreate"]["stagedTargets"]
    if not staged_targets:
        print(f"  ERROR: No staged targets returned")
        return False

    staged_target = staged_targets[0]
    upload_url = staged_target["url"]
    resource_url = staged_target["resourceUrl"]
    parameters = {p["name"]: p["value"] for p in staged_target["parameters"]}

    print(f"  Uploading to staged URL...")

    # Upload file to staged URL
    files = {"file": (filename, BytesIO(image_data), "image/png")}
    upload_response = requests.post(upload_url, data=parameters, files=files, timeout=60)

    if upload_response.status_code not in (200, 201, 204):
        print(f"  ERROR: Upload failed with status {upload_response.status_code}")
        return False

    print(f"  Uploaded successfully")

    # Create media from staged upload
    print(f"  Creating product media...")

    create_media_mutation = """
    mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
        productCreateMedia(media: $media, productId: $productId) {
            media {
                ... on MediaImage {
                    id
                    image {
                        url
                    }
                    alt
                }
            }
            mediaUserErrors {
                field
                message
            }
            userErrors {
                field
                message
            }
        }
    }
    """

    media_variables = {
        "productId": product_id,
        "media": [{
            "originalSource": resource_url,
            "alt": alt_text,
            "mediaContentType": "IMAGE"
        }]
    }

    media_result = client.execute_graphql(create_media_mutation, media_variables)

    if not media_result or "data" not in media_result:
        print(f"  ERROR: Failed to create media - no result")
        print(f"  Response: {media_result}")
        return False

    create_media_data = media_result["data"].get("productCreateMedia")
    if not create_media_data:
        print(f"  ERROR: No productCreateMedia in response")
        print(f"  Response: {media_result}")
        return False

    errors = create_media_data.get("mediaUserErrors", [])
    user_errors = create_media_data.get("userErrors", [])

    if errors or user_errors:
        print(f"  ERROR: Media errors: {errors or user_errors}")
        return False

    media = create_media_data.get("media", [])
    if media and len(media) > 0:
        media_item = media[0]
        if media_item:
            image_data = media_item.get("image")
            if image_data:
                new_image_url = image_data.get("url", "")
                print(f"  New image URL: {new_image_url[:70]}...")
            else:
                print(f"  Media created (no image URL yet)")
        else:
            print(f"  Media created (item is None)")
    else:
        print(f"  Media created (no media in response)")

    return True

def delete_old_image(client, product_id, media_id):
    """Delete old image"""
    print(f"  Deleting old image...")

    mutation = """
    mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
        productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
            deletedMediaIds
            userErrors {
                field
                message
            }
        }
    }
    """

    variables = {
        "productId": product_id,
        "mediaIds": [media_id]
    }

    result = client.execute_graphql(mutation, variables)

    if result and "data" in result:
        deleted = result["data"]["productDeleteMedia"].get("deletedMediaIds", [])
        if deleted:
            print(f"  Deleted old image")
            return True

    print(f"  WARNING: Could not delete old image")
    return False

def get_current_media(client, product_id):
    """Get current product media"""
    query = """
    query getProduct($id: ID!) {
        product(id: $id) {
            media(first: 10) {
                edges {
                    node {
                        ... on MediaImage {
                            id
                            image {
                                url
                            }
                        }
                    }
                }
            }
        }
    }
    """

    result = client.execute_graphql(query, {"id": product_id})

    if result and "data" in result:
        product = result["data"].get("product")
        if product:
            return product.get("media", {}).get("edges", [])

    return []

def main():
    client = ShopifyClient()
    client.authenticate()

    framework = get_framework()

    print("\n" + "="*60)
    print("AUTO-FIX IMAGES - APPLY SQUARING TRANSFORMATION")
    print("="*60)

    for product in PRODUCTS:
        print(f"\n{'='*60}")
        print(f"Product: {product['title']}")
        print(f"SKU: {product['sku']}")
        print(f"{'='*60}")

        try:
            # Step 0: Get current image URL
            print(f"  Fetching current image URL...")
            current_media = get_current_media(client, product["product_id"])
            if not current_media:
                print(f"  ERROR: No images found on product")
                continue

            current_image_url = current_media[0]["node"]["image"]["url"]
            print(f"  Current URL: {current_image_url[:70]}...")

            # Step 1: Download current image
            image_data = download_image(current_image_url)

            # Step 2: Apply squaring transformation
            print(f"\n  Applying squaring transformation...")
            transformed_data = apply_squaring_transformation(image_data)

            # Step 3: Generate filename and alt text
            print(f"\n  Generating metadata...")
            product_context = {
                "vendor": product["vendor"].lower(),
                "product_line": product["title"].lower().replace(" ", "-").replace(",", ""),
                "variant_name": product["sku"],
                "ext": "png"
            }

            filename = f"{product['vendor'].lower()}-{product['sku']}.png"
            alt_text = f"{product['title']} - {product['vendor']}"

            print(f"  Filename: {filename}")
            print(f"  Alt text: {alt_text}")

            # Step 4: Get current media IDs
            print(f"\n  Getting current media...")
            current_media = get_current_media(client, product["product_id"])
            old_media_ids = [edge["node"]["id"] for edge in current_media]

            # Step 5: Upload new image
            print(f"\n  Uploading transformed image...")
            success = upload_image_to_shopify(
                client,
                product["product_id"],
                transformed_data,
                filename,
                alt_text
            )

            if not success:
                print(f"  ERROR: Upload failed")
                continue

            # Step 6: Delete old images
            if old_media_ids:
                print(f"\n  Cleaning up old images...")
                for media_id in old_media_ids:
                    delete_old_image(client, product["product_id"], media_id)

            # Step 7: Verify new image
            print(f"\n  Verifying new image...")
            import time
            time.sleep(2)  # Wait for Shopify to process

            # Get new media
            new_media = get_current_media(client, product["product_id"])
            if new_media:
                new_image_url = new_media[0]["node"]["image"]["url"]

                verification = verify_and_fix_product_image(
                    product_id=product["product_id"],
                    image_url=new_image_url,
                    product_title=product["title"],
                    vendor=product["vendor"],
                    image_type="product",
                    shopify_client=client,
                    auto_fix=False
                )

                if verification.get("needs_recrop"):
                    print(f"  VERIFICATION: Still needs attention")
                    print(f"    Issue: {verification.get('issue')}")
                else:
                    print(f"  VERIFICATION: OK (confidence: {verification.get('confidence', 0):.0%})")

            print(f"\n  SUCCESS: Image fixed and uploaded")

        except Exception as e:
            print(f"\n  ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("AUTO-FIX COMPLETE")
    print('='*60)

if __name__ == "__main__":
    main()
