"""
Ralph Wiggum Integration for Product Quality Agent

Iterative loop that continuously improves product quality until target score reached.

Usage:
    python orchestrator/quality_loop_ralph.py --limit 20 --target-score 85 --max-iterations 10
"""

import os
import sys
import json
import argparse
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.product_quality_agent import ProductQualityAgent


def check_quality_target_reached(master_file, target_score, limit):
    """
    Check if quality target has been reached.

    Returns:
        tuple: (bool: target_reached, str: status_message, dict: stats)
    """
    if not os.path.exists(master_file):
        return False, "No master file found", {}

    with open(master_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    products = data.get('products', {})

    # Filter to only products in our limit
    sorted_products = sorted(
        products.items(),
        key=lambda x: x[1].get('completeness_score', 0)
    )[:limit]

    if not sorted_products:
        return False, "No products found", {}

    scores = [p[1].get('completeness_score', 0) for p in sorted_products]
    below_target = [s for s in scores if s < target_score]

    avg_score = sum(scores) / len(scores) if scores else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0

    stats = {
        'total_products': len(sorted_products),
        'avg_score': avg_score,
        'min_score': min_score,
        'max_score': max_score,
        'below_target': len(below_target),
        'target_score': target_score
    }

    if len(below_target) == 0:
        return True, f"[OK] All {len(sorted_products)} products meet target ({target_score}+)", stats
    else:
        return False, f"[PENDING] {len(below_target)}/{len(sorted_products)} products below target", stats


def main():
    parser = argparse.ArgumentParser(description="Ralph Wiggum Quality Loop")
    parser.add_argument("--limit", type=int, default=20, help="Number of products to process")
    parser.add_argument("--target-score", type=int, default=85, help="Target quality score (0-100)")
    parser.add_argument("--max-iterations", type=int, default=10, help="Max iterations before stopping")
    parser.add_argument("--master-file", default="data/product_quality_master.json", help="Master data file")

    args = parser.parse_args()

    print("=" * 70)
    print("Ralph Wiggum Quality Loop")
    print("=" * 70)
    print(f"Target: {args.target_score}/100")
    print(f"Products: {args.limit}")
    print(f"Max iterations: {args.max_iterations}")
    print("=" * 70)
    print()

    # Run quality check with auto-repair
    print("[STEP 1/3] Running quality scan with auto-repair...")
    print()

    python_exe = "./venv/Scripts/python.exe" if os.path.exists("./venv/Scripts/python.exe") else "python"

    cmd = [
        python_exe,
        "orchestrator/product_quality_agent.py",
        "--scan-all",
        "--limit", str(args.limit),
        "--auto-repair"
    ]

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print("\n[ERROR] Quality scan failed")
        return 1

    print()
    print("[STEP 2/3] Checking if target reached...")
    print()

    # Check if target reached
    target_reached, status_msg, stats = check_quality_target_reached(
        args.master_file,
        args.target_score,
        args.limit
    )

    # Print stats
    print(f"   Products checked: {stats.get('total_products', 0)}")
    print(f"   Average score: {stats.get('avg_score', 0):.1f}/100")
    print(f"   Score range: {stats.get('min_score', 0)}-{stats.get('max_score', 0)}/100")
    print(f"   Below target: {stats.get('below_target', 0)}")
    print()
    print(f"   Status: {status_msg}")
    print()

    # Output completion promise if target reached
    if target_reached:
        print("[STEP 3/3] Target reached!")
        print()
        print("=" * 70)
        print("QUALITY TARGET ACHIEVED!")
        print("=" * 70)
        print()
        print("<promise>QUALITY_TARGET_REACHED</promise>")
        return 0
    else:
        print("[STEP 3/3] Target not yet reached - continuing loop...")
        print()
        print("=" * 70)
        print("Iteration complete - will continue improving...")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
