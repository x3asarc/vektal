import os
import shutil
from pathlib import Path

def organize_workspace():
    """Ensure all files are in their correct locations."""
    root = Path(".")
    
    # Define directory structure
    dirs = {
        "scripts": [".py"],
        "data": ["products.csv", "not_found.csv", "push_proof.csv", "shopify_itd_products.csv"],
        "data/archive": ["push_proof_backup.csv", "push_proof_old.csv"],
        "logs": [".log"],
        "temp": ["preview_results.csv", "batch_1_preview.csv"]
    }
    
    # Files that MUST stay in the root
    keep_in_root = ["app.py", "image_scraper.py", "PROJECT_SUMMARY.md", "README_APP.md", "SETUP.md", 
                     "requirements.txt", ".env", ".env.example", ".gitignore", "scraper_app.db"]

    # Ensure directories exist
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    
    # Special folders for web
    (root / "web/static").mkdir(parents=True, exist_ok=True)
    (root / "web/templates").mkdir(parents=True, exist_ok=True)

    # Move files
    for file_path in root.glob("*"):
        if not file_path.is_file():
            continue
            
        name = file_path.name
        ext = file_path.suffix.lower()
        
        if name in keep_in_root:
            continue
            
        # Specific file matches
        moved = False
        for target_dir, patterns in dirs.items():
            if name in patterns or ext in patterns:
                # Basic protection for scraper/app scripts
                if name == "app.py" or name == "image_scraper.py":
                    continue
                
                print(f"Moving {name} -> {target_dir}/")
                shutil.move(str(file_path), str(root / target_dir / name))
                moved = True
                break
                
    print("Workspace organization check complete.")

if __name__ == "__main__":
    organize_workspace()
