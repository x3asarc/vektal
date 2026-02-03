"""
Use OpenRouter API with Gemini 2.0 Flash to visually verify image types
- Download the 7 images from Juno Rose
- Analyze each with vision AI
- Verify proposed filenames and alt text are appropriate
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import pandas as pd
import requests
from src.core.shopify_resolver import ShopifyResolver
import base64
from io import BytesIO

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY environment variable not set")
    print("Please set it with your OpenRouter API key")
    sys.exit(1)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.0-flash-001"

def analyze_image_with_vision(image_url, image_index):
    """
    Use Gemini 2.0 Flash to analyze what the image shows

    Returns:
        dict with description, image_type, suggested_filename, suggested_alt
    """
    print(f"\n  [{image_index}/7] Analyzing image with Gemini 2.0 Flash...")
    print(f"    URL: {image_url[:80]}...")

    # Prepare the vision prompt
    prompt = """Analyze this product image and provide:

1. **Image Type**: Classify as one of:
   - groupshot (multiple product variants shown together)
   - detail (close-up of product texture, flakes, or effect)
   - packshot (product container/jar on plain background)
   - lifestyle (product in use or styled scene)
   - other (specify what it shows)

2. **Description**: Describe what you see in 1-2 sentences

3. **Suggested Filename**: Propose SEO-friendly filename (e.g., pentart-galaxy-flakes-15g-groupshot.jpg)

4. **Suggested Alt Text**: SEO-optimized alt text in German describing the image

Format your response as:
TYPE: [image_type]
DESCRIPTION: [description]
FILENAME: [suggested_filename]
ALT: [suggested_alt_text]
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        "max_tokens": 500
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result['choices'][0]['message']['content']

        # Parse the response
        lines = content.strip().split('\n')
        parsed = {}

        for line in lines:
            if line.startswith('TYPE:'):
                parsed['type'] = line.replace('TYPE:', '').strip()
            elif line.startswith('DESCRIPTION:'):
                parsed['description'] = line.replace('DESCRIPTION:', '').strip()
            elif line.startswith('FILENAME:'):
                parsed['filename'] = line.replace('FILENAME:', '').strip()
            elif line.startswith('ALT:'):
                parsed['alt'] = line.replace('ALT:', '').strip()

        print(f"    Type: {parsed.get('type', 'unknown')}")
        print(f"    Description: {parsed.get('description', 'N/A')[:80]}...")

        return parsed

    except Exception as e:
        print(f"    ERROR: {e}")
        return None


print("="*80)
print("VERIFY IMAGE TYPES WITH VISION AI")
print("="*80)
print(f"\nUsing: {MODEL} via OpenRouter API\n")

# Connect to Shopify
print("[1/3] Connecting to Shopify...")
resolver = ShopifyResolver()
print("  Connected")

# Get Juno Rose images
juno_rose_gid = "gid://shopify/Product/6665942925469"

print("\n[2/3] Getting images from Juno Rose...")

query = """
query getProduct($id: ID!) {
  product(id: $id) {
    title
    media(first: 20) {
      edges {
        node {
          id
          alt
          ... on MediaImage {
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

result = resolver.client.execute_graphql(query, {"id": juno_rose_gid})
juno_rose = result.get('data', {}).get('product')

media_list = juno_rose.get('media', {}).get('edges', [])
shared_images = media_list[1:]  # Skip the first (new primary)

print(f"  Found {len(shared_images)} shared images to analyze")

# Load SEO plan for comparison
script_dir = Path(__file__).parent
seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"
seo_df = pd.read_csv(seo_plan_path)

# Get proposed names from SEO plan
non_primary = seo_df[seo_df['is_primary'] == False]
clusters = {}
for cluster_id in non_primary['cluster_id'].unique():
    cluster_rows = non_primary[non_primary['cluster_id'] == cluster_id]
    first_row = cluster_rows.iloc[0]
    clusters[cluster_id] = {
        'filename': first_row['proposed_filename'],
        'alt': first_row['proposed_alt'],
        'shot_type': first_row['shot_type']
    }

sorted_clusters = sorted(clusters.items(), key=lambda x: (x[1]['shot_type'] == 'groupshot', -len(non_primary[non_primary['cluster_id'] == x[0]])))

# Analyze each image
print("\n[3/3] Analyzing images with Vision AI...")

results = []

for i, edge in enumerate(shared_images, 1):
    node = edge['node']
    image_url = node.get('image', {}).get('url', '')
    current_filename = image_url.split('/')[-1].split('?')[0]

    print(f"\n{'='*80}")
    print(f"IMAGE {i}/7")
    print(f"{'='*80}")
    print(f"  Current filename: {current_filename[:60]}")

    # Get proposed mapping from SEO plan
    if i <= len(sorted_clusters):
        cluster_id, cluster_info = sorted_clusters[i-1]
        proposed_filename = cluster_info['filename']
        proposed_alt = cluster_info['alt']
        proposed_type = cluster_info['shot_type']

        print(f"\n  [PROPOSED FROM SEO PLAN]")
        print(f"    Cluster: {cluster_id}")
        print(f"    Type: {proposed_type}")
        print(f"    Filename: {proposed_filename}")
        print(f"    Alt: {proposed_alt[:60]}...")
    else:
        proposed_filename = "unknown"
        proposed_alt = "unknown"
        proposed_type = "unknown"

    # Analyze with Vision AI
    print(f"\n  [VISION AI ANALYSIS]")
    analysis = analyze_image_with_vision(image_url, i)

    if analysis:
        print(f"\n  [AI SUGGESTION]")
        print(f"    Type: {analysis.get('type', 'N/A')}")
        print(f"    Filename: {analysis.get('filename', 'N/A')}")
        print(f"    Alt: {analysis.get('alt', 'N/A')[:60]}...")

        # Compare
        print(f"\n  [COMPARISON]")
        type_match = analysis.get('type', '').lower() == proposed_type.lower()
        print(f"    Type match: {'YES' if type_match else 'NO'}")

        if not type_match:
            print(f"      Proposed: {proposed_type}")
            print(f"      AI sees: {analysis.get('type', 'N/A')}")

    results.append({
        'image_num': i,
        'current_filename': current_filename,
        'proposed_type': proposed_type,
        'proposed_filename': proposed_filename,
        'proposed_alt': proposed_alt[:100],
        'ai_type': analysis.get('type', 'N/A') if analysis else 'ERROR',
        'ai_filename': analysis.get('filename', 'N/A') if analysis else 'ERROR',
        'ai_alt': analysis.get('alt', 'N/A')[:100] if analysis else 'ERROR',
        'ai_description': analysis.get('description', 'N/A') if analysis else 'ERROR'
    })

# Summary
print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}\n")

print("Results:")
print()

for r in results:
    print(f"Image {r['image_num']}: {r['current_filename'][:50]}")
    print(f"  Proposed: {r['proposed_type']} -> {r['proposed_filename']}")
    print(f"  AI sees: {r['ai_type']}")
    print(f"  AI description: {r['ai_description'][:70]}...")

    match = r['ai_type'].lower() == r['proposed_type'].lower()
    print(f"  Match: {'YES' if match else 'NO - NEEDS REVIEW'}")
    print()

# Save results
output_path = script_dir / "data" / "shared_images" / "galaxy_flakes" / "vision_analysis_results.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)

df = pd.DataFrame(results)
df.to_csv(output_path, index=False)

print(f"Results saved to: {output_path}")
print()
print("Review the AI suggestions and verify they match the proposed assignments")
print("before proceeding with the image restoration operation.")
