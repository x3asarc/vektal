import os
import shutil
import glob
import time

def auto_organize():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to root
    root_dir = os.path.dirname(base_dir)
    os.chdir(root_dir)

    print(f"Organizing files in {root_dir}...")

    # Define mappings (Pattern -> Directory)
    mappings = {
        "results": [
            "*_push_summary_*.csv",
            "*_results_*.csv",
            "scrape_live_summary_*.csv",
            "preview_results.csv",
            "debug_results.csv",
            "metadata_push_summary_*.csv",
            "image_push_summary_*.csv"
        ],
        "data": [
            "products.csv",
            "push_proof.csv",
            "all_itd_prices_update.csv",
            "itd_ean_repaired.csv",
            "not_found.csv",
            "final_push_data*.csv"
        ],
        "temp": [
            "paperdesigns_inventory.csv",
            "paperdesigns_push_ready.csv",
            "merged_itd_corrections.csv",
            "debug_test.csv",
            "push_proof_before_metadata.csv",
            "itd_short_eans.csv",
            "prep_data_for_push.py",
            "test_products.csv"
        ],
        "logs": [
            "*.log",
            "test_summary.md"
        ],
        "scripts": [
            "add_metadata_columns.py",
            "fix_itd_pricing.py",
            "prep_all_itd_prices.py",
            "find_correct_eans.py",
            "debug_ean.py",
            "itd_debug.py",
            "export_paperdesigns.py",
            "list_vendors.py",
            "sync_to_proof.py",
            "cleanup_workspace.py",
            "not_found_finder_v4_optimized.py",
            "update_metadata.py"
        ]
    }

    # Ensure target directories exist
    for d in mappings.keys():
        if not os.path.exists(d):
            os.makedirs(d)

    # Process files
    moved_count = 0
    for folder, patterns in mappings.items():
        for pattern in patterns:
            for f in glob.glob(pattern):
                if os.path.isfile(f):
                    dest = os.path.join(folder, f)
                    
                    # Handle existing file by timestamping
                    if os.path.exists(dest):
                        timestamp = int(os.path.getctime(f))
                        name, ext = os.path.splitext(f)
                        dest = os.path.join(folder, f"{name}_{timestamp}{ext}")
                    
                    try:
                        shutil.move(f, dest)
                        print(f"  Moved {f} -> {dest}")
                        moved_count += 1
                    except Exception as e:
                        print(f"  Failed to move {f}: {e}")

    print(f"\nReorganization complete. Total files moved: {moved_count}")

if __name__ == "__main__":
    auto_organize()
