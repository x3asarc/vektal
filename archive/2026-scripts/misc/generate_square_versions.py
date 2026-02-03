"""
Generate 3 square versions of Saturn green image
All with transparent backgrounds
"""
import os
from PIL import Image
from pathlib import Path

# Paths
input_path = Path("data/supplier_images/galaxy_flakes/pentart-galaxy-flakes-15g-saturn-green.jpg")
output_dir = Path("data/supplier_images/galaxy_flakes/square_tests")
output_dir.mkdir(parents=True, exist_ok=True)

print("="*80)
print("Generating Square Image Versions with Transparent Backgrounds")
print("="*80)

# Load original image
print(f"\nLoading: {input_path}")
img = Image.open(input_path)
original_size = img.size
print(f"Original size: {original_size[0]}x{original_size[1]}")

# Convert to RGBA for transparency
if img.mode != 'RGBA':
    img = img.convert('RGBA')
    print("Converted to RGBA (with alpha channel)")

# Determine square size (use smaller dimension or average)
square_size = 900  # Use the smaller dimension from 1719x900

print(f"\nTarget square size: {square_size}x{square_size}")
print(f"\nGenerating 3 versions...\n")

# VERSION 1: Center Crop
print("[1/3] Center Crop - Take 900x900 from center")
center_crop = img.copy()
width, height = center_crop.size

# Calculate crop box for center
left = (width - square_size) // 2
top = (height - square_size) // 2
right = left + square_size
bottom = top + square_size

# For center crop, we need a different approach since image is wider than tall
# Take the center square by cropping width
left = (width - height) // 2
right = left + height
center_crop_img = center_crop.crop((left, 0, right, height))

# Now resize to target square size
center_crop_img = center_crop_img.resize((square_size, square_size), Image.Resampling.LANCZOS)

output1 = output_dir / "saturn-green-center-crop.png"
center_crop_img.save(output1, 'PNG')
print(f"   Saved: {output1}")
print(f"   Size: {center_crop_img.size}")
print(f"   Method: Cropped center square from original, resized to {square_size}x{square_size}")

# VERSION 2: Contain with Transparent Padding
print("\n[2/3] Contain with Padding - Fit image in square with transparent borders")
contain_img = Image.new('RGBA', (square_size, square_size), (0, 0, 0, 0))  # Transparent background

# Calculate scaling to fit within square
scale = square_size / max(width, height)
new_width = int(width * scale)
new_height = int(height * scale)

# Resize original
resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

# Paste centered on transparent background
x_offset = (square_size - new_width) // 2
y_offset = (square_size - new_height) // 2
contain_img.paste(resized, (x_offset, y_offset), resized)

output2 = output_dir / "saturn-green-contain-padding.png"
contain_img.save(output2, 'PNG')
print(f"   Saved: {output2}")
print(f"   Size: {contain_img.size}")
print(f"   Method: Scaled to fit, centered with transparent padding")

# VERSION 3: Cover Crop - Zoom to fill square
print("\n[3/3] Cover Crop - Zoom to fill square (crops top/bottom)")

# Calculate scaling to cover the square (zoom in)
scale = square_size / min(width, height)
new_width = int(width * scale)
new_height = int(height * scale)

# Resize
resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

# Crop center
left = (new_width - square_size) // 2
top = (new_height - square_size) // 2
cover_img = resized.crop((left, top, left + square_size, top + square_size))

output3 = output_dir / "saturn-green-cover-crop.png"
cover_img.save(output3, 'PNG')
print(f"   Saved: {output3}")
print(f"   Size: {cover_img.size}")
print(f"   Method: Scaled up to fill, cropped to square")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nAll images saved to: {output_dir}")
print(f"\nGenerated versions:")
print(f"  1. {output1.name} - Center crop")
print(f"  2. {output2.name} - Contain with transparent padding")
print(f"  3. {output3.name} - Cover crop (zoomed)")
print(f"\nAll images:")
print(f"  - Size: {square_size}x{square_size} (1:1 square)")
print(f"  - Format: PNG with transparency")
print(f"  - Background: Transparent")
print(f"\nReview images and select preferred version!")
