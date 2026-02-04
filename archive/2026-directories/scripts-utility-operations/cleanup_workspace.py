import os
import shutil
import glob

def cleanup():
    # Ensure directories exist
    dirs = ["results", "data", "logs", "temp", "scripts", "archive"]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)

    # Move Results/Summaries
    res_patterns = [
        "image_push_summary_*.csv",
        "metadata_push_summary_*.csv",
        "test_results_*.csv",
        "debug_results.csv",
        "image_push_summary.csv" # If exists
    ]
    for pattern in res_patterns:
        for f in glob.glob(pattern):
            dest = os.path.join("results", f)
            # Handle collision
            if os.path.exists(dest):
                dest = os.path.join("results", f.replace(".csv", f"_{int(os.path.getctime(f))}.csv"))
            shutil.move(f, dest)

    # Move Logs
    for f in glob.glob("*.log"):
        shutil.move(f, os.path.join("logs", f))

    # Move Temp/Working files
    temp_files = [
        "paperdesigns_inventory.csv",
        "paperdesigns_push_ready.csv",
        "final_push_data.csv",
        "final_push_data_clean.csv",
        "final_push_data_ready.csv",
        "merged_itd_corrections.csv",
        "debug_test.csv",
        "push_proof_before_metadata.csv",
        "itd_short_eans.csv" # This looks like a middle-step file
    ]
    for f in temp_files:
        if os.path.exists(f):
            shutil.move(f, os.path.join("temp", f))

    # Move Scripts to scripts/
    script_files = [
        "add_metadata_columns.py",
        "fix_itd_pricing.py",
        "prep_all_itd_prices.py",
        "find_correct_eans.py",
        "debug_ean.py",
        "itd_debug.py",
        "export_paperdesigns.py",
        "list_vendors.py",
        "prep_data_for_push.py",
        "sync_to_proof.py"
    ]
    for f in script_files:
        if os.path.exists(f):
            shutil.move(f, os.path.join("scripts", f))

    print("Cleanup complete. Files reorganized.")

if __name__ == "__main__":
    cleanup()
