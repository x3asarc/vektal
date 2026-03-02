import os
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.models.pending_approvals import PendingApproval
from src.app_factory import create_app

def create_test_approval():
    # The app should load DB settings from the existing environment/.env.
    if not os.getenv("DATABASE_URL"):
        print("DATABASE_URL is not set; skipping test approval creation.")
        return

    app = create_app()
    with app.app_context():
        approval = PendingApproval.create_approval(
            type='code_change',
            title='Test approval from CLI verification',
            description='This is a test approval for Phase 15.1 verification.',
            diff='--- a/src/core/logic.py\n+++ b/src/core/logic.py\n@@ -1,1 +1,1 @@\n-old\n+new',
            confidence=0.85,
            blast_radius_files=1,
            blast_radius_loc=10
        )
        print(f"Created test approval: {approval.approval_id}")

if __name__ == '__main__':
    create_test_approval()
