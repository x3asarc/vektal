#!/usr/bin/env python3
"""SHA discipline gate — detects stale HEAD SHA in CI comments and PR review requests.

Prevents re-running stale automation comments from a different commit than the current HEAD.
Reads PR comments from STDIN (JSON array) or from a GitHub API response file.

Usage:
    # Check if a bot comment SHA matches current HEAD
    python scripts/governance/sha_gate.py --head-sha <sha> --comment-sha <sha>

    # Parse a batch of comments (JSON array) from stdin and emit stale ones
    python scripts/governance/sha_gate.py --head-sha <sha> --comments-file <path>

    # Emit a deduplicated rerun comment body (idempotent)
    python scripts/governance/sha_gate.py --emit-rerun --head-sha <sha> --check <check_name>

Exit codes:
    0 — SHA matches (or emit mode, always 0)
    1 — SHA mismatch (stale comment detected)
    2 — usage / config error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


BOT_MARKER = "<!-- sha-gate-bot -->"
SHA_TAG_PREFIX = "<!-- sha:"
SHA_TAG_SUFFIX = " -->"


def sha_tag(sha: str) -> str:
    return f"{SHA_TAG_PREFIX}{sha}{SHA_TAG_SUFFIX}"


def extract_sha_from_comment(body: str) -> str | None:
    """Extract embedded SHA from a bot comment body."""
    start = body.find(SHA_TAG_PREFIX)
    if start == -1:
        return None
    end = body.find(SHA_TAG_SUFFIX, start + len(SHA_TAG_PREFIX))
    if end == -1:
        return None
    return body[start + len(SHA_TAG_PREFIX):end].strip()


def is_bot_comment(body: str) -> bool:
    return BOT_MARKER in body


def build_rerun_comment(head_sha: str, check_name: str, context: str = "") -> str:
    """Build an idempotent rerun-request comment body."""
    short_sha = head_sha[:8]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dedup_key = hashlib.sha256(f"{head_sha}:{check_name}".encode()).hexdigest()[:12]
    lines = [
        BOT_MARKER,
        sha_tag(head_sha),
        f"<!-- dedup:{dedup_key} -->",
        "",
        f"### CI Rerun Request -- `{check_name}`",
        "",
        f"**SHA:** `{short_sha}` | **Requested at:** `{ts}`",
    ]
    if context:
        lines += ["", f"**Context:** {context}"]
    lines += [
        "",
        f"Trigger: `/rerun {check_name}` on commit `{head_sha}`",
        "",
        "_This comment is machine-generated and SHA-pinned. Stale comments are ignored._",
    ]
    return "\n".join(lines)


def check_single_sha(head_sha: str, comment_sha: str) -> int:
    if head_sha == comment_sha:
        print(f"SHA match: {head_sha[:8]} OK")
        return 0
    print(
        f"SHA mismatch: comment is for {comment_sha[:8]}, HEAD is {head_sha[:8]}. "
        "Comment is stale — skipping rerun.",
        file=sys.stderr,
    )
    return 1


def check_comments_file(head_sha: str, comments_file: Path) -> int:
    if not comments_file.exists():
        print(f"ERROR: comments file not found: {comments_file}", file=sys.stderr)
        return 2
    comments = json.loads(comments_file.read_text(encoding="utf-8"))
    stale = []
    for comment in comments:
        body = comment.get("body", "")
        if not is_bot_comment(body):
            continue
        embedded_sha = extract_sha_from_comment(body)
        if embedded_sha and embedded_sha != head_sha:
            stale.append({"id": comment.get("id"), "sha": embedded_sha})
    result = {
        "head_sha": head_sha,
        "stale_comments": stale,
        "stale_count": len(stale),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if stale else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SHA discipline gate")
    parser.add_argument("--head-sha", required=True, help="Current HEAD commit SHA")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--comment-sha", help="SHA embedded in a single bot comment")
    mode.add_argument("--comments-file", type=Path, help="JSON file with array of PR comments")
    mode.add_argument("--emit-rerun", action="store_true", help="Emit a rerun comment body")
    parser.add_argument("--check", default="ci", help="Check name (used with --emit-rerun)")
    parser.add_argument("--context", default="", help="Optional context string for rerun comment")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.emit_rerun:
        print(build_rerun_comment(args.head_sha, args.check, args.context))
        return 0

    if args.comment_sha:
        return check_single_sha(args.head_sha, args.comment_sha)

    if args.comments_file:
        return check_comments_file(args.head_sha, args.comments_file)

    print("ERROR: must specify --comment-sha, --comments-file, or --emit-rerun", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
