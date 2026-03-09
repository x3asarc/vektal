#!/usr/bin/env python3
"""Fix encoding issues in memory files by converting Windows-1252 to UTF-8."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.text_sanitizer import WINDOWS_1252_TO_ASCII


def scan_file(file_path: Path) -> tuple[bool, str | None]:
    """
    Scan a file for encoding issues.

    Returns:
        (has_issue, error_message) tuple
    """
    try:
        file_path.read_text(encoding="utf-8")
        return False, None
    except UnicodeDecodeError as e:
        return True, str(e)


def fix_file(file_path: Path, *, dry_run: bool = False) -> tuple[bool, int]:
    """
    Fix encoding issues in a file.

    Args:
        file_path: Path to the file to fix
        dry_run: If True, don't actually write the fixed file

    Returns:
        (fixed, replacements) tuple where fixed is True if the file was fixed
    """
    try:
        # Try UTF-8 first
        content = file_path.read_text(encoding="utf-8")
        return False, 0
    except UnicodeDecodeError:
        pass

    # Read with windows-1252 and fix
    try:
        content = file_path.read_text(encoding="windows-1252")
    except Exception as e:
        print(f"  ERROR: Cannot read {file_path}: {e}")
        return False, 0

    # Replace Windows-1252 characters
    replacements = 0
    fixed_content = content
    for win_char, ascii_char in WINDOWS_1252_TO_ASCII.items():
        count = fixed_content.count(win_char)
        if count > 0:
            fixed_content = fixed_content.replace(win_char, ascii_char)
            replacements += count

    if replacements == 0:
        print(f"  WARNING: {file_path} has encoding issues but no known fixes applied")
        return False, 0

    if not dry_run:
        # Create backup
        backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
        if not backup_path.exists():
            backup_path.write_bytes(file_path.read_bytes())

        # Write fixed content
        file_path.write_text(fixed_content, encoding="utf-8")

    return True, replacements


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix encoding issues in memory files")
    parser.add_argument(
        "--memory-root",
        type=Path,
        default=REPO_ROOT / ".memory",
        help="Memory root directory (default: .memory/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan for issues without fixing",
    )
    args = parser.parse_args()

    memory_root = args.memory_root.resolve()
    if not memory_root.exists():
        print(f"ERROR: Memory root does not exist: {memory_root}")
        return 1

    print(f"Scanning memory files in: {memory_root}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'FIX'}\n")

    issues_found = []
    files_scanned = 0

    for root_dir, dirs, files in os.walk(memory_root):
        for file in files:
            if file.endswith((".json", ".jsonl", ".md")):
                file_path = Path(root_dir) / file
                files_scanned += 1

                has_issue, error = scan_file(file_path)
                if has_issue:
                    issues_found.append(file_path)
                    rel_path = file_path.relative_to(REPO_ROOT)
                    print(f"[ISSUE] {rel_path}")
                    if error:
                        print(f"  Error: {error}")

                    if not args.dry_run:
                        fixed, replacements = fix_file(file_path, dry_run=args.dry_run)
                        if fixed:
                            print(f"  [FIXED] Replaced {replacements} characters")
                        else:
                            print(f"  [SKIP] Could not fix automatically")

    print(f"\n{'='*60}")
    print(f"Files scanned: {files_scanned}")
    print(f"Issues found: {len(issues_found)}")

    if args.dry_run and issues_found:
        print("\nRun without --dry-run to fix these files.")
        return 1

    if not args.dry_run and issues_found:
        print("\nAll issues have been fixed. Backups created with .backup extension.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
