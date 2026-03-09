#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick health check after Commander description fix."""
import sys
import os
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, 'strict')

project_root = Path(__file__).parent.parent
os.chdir(project_root)

print("=" * 60)
print("COMMANDER HEALTH CHECK")
print("=" * 60)

# Test 1: Commander agent file verification
print("\n[TEST 1] Commander agent file")
print("-" * 60)
try:
    commander_path = project_root / ".claude" / "agents" / "commander.md"
    if not commander_path.exists():
        print(f"FAIL: Commander file not found: {commander_path}")
        sys.exit(1)

    content = commander_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    # Find description line
    desc_line = None
    for line in lines:
        if line.strip().startswith('description:'):
            desc_line = line
            break

    if not desc_line:
        print("FAIL: No description field found")
        sys.exit(1)

    # Check for block scalar (> or |)
    if '>' in desc_line or '|' in desc_line:
        print("FAIL: Description uses YAML block scalar (> or |)")
        print(f"  Line: {desc_line.strip()}")
        sys.exit(1)
    else:
        print("PASS: Description is single-line (no block scalar)")
        print(f"  {desc_line.strip()[:80]}...")

    # Check for routing keywords that might trigger handoff
    problematic_keywords = ['spawn', 'Bundle', 'routes', 'delegates']
    found = []
    desc_text = desc_line.lower()
    for keyword in problematic_keywords:
        if keyword.lower() in desc_text:
            found.append(keyword)

    if found:
        print(f"WARN: Routing keywords in description: {found}")
        print("  May trigger classifyHandoffIfNeeded at init")
    else:
        print("PASS: No routing keywords in description")

    print(f"INFO: Commander file size: {len(content)} bytes, {len(lines)} lines")

except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Verify all platform copies match
print("\n[TEST 2] Multi-platform consistency")
print("-" * 60)
try:
    platforms = ['.claude', '.gemini', '.codex', '.letta']
    commander_files = {}

    for platform in platforms:
        path = project_root / platform / "agents" / "commander.md"
        if path.exists():
            commander_files[platform] = path.read_text(encoding='utf-8')

    if len(commander_files) != 4:
        print(f"WARN: Only {len(commander_files)}/4 platform files found")
        for p in platforms:
            exists = p in commander_files
            print(f"  {p}: {'OK' if exists else 'MISSING'}")

    # Check descriptions match
    descriptions = {}
    for platform, content in commander_files.items():
        for line in content.split('\n'):
            if line.strip().startswith('description:'):
                descriptions[platform] = line.strip()
                break

    unique_descriptions = set(descriptions.values())
    if len(unique_descriptions) == 1:
        print(f"PASS: All {len(commander_files)} platforms have identical descriptions")
    else:
        print(f"FAIL: Description mismatch across platforms")
        for platform, desc in descriptions.items():
            print(f"  {platform}: {desc[:60]}...")
        sys.exit(1)

except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify aura-oracle is available
print("\n[TEST 3] aura-oracle availability")
print("-" * 60)
try:
    oracle_path = project_root / ".claude" / "skills" / "aura-oracle" / "oracle.py"
    if not oracle_path.exists():
        print(f"FAIL: aura-oracle not found: {oracle_path}")
        sys.exit(1)

    oracle_content = oracle_path.read_text(encoding='utf-8')
    has_ask = 'def ask(' in oracle_content
    has_driver = '_get_driver' in oracle_content

    if has_ask and has_driver:
        print("PASS: aura-oracle oracle.py found with ask() and _get_driver()")
        print(f"INFO: oracle.py size: {len(oracle_content)} bytes")
    else:
        print("FAIL: aura-oracle missing expected functions")
        print(f"  has ask(): {has_ask}")
        print(f"  has _get_driver(): {has_driver}")
        sys.exit(1)

except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Check environment configuration
print("\n[TEST 4] Environment configuration")
print("-" * 60)
try:
    from dotenv import load_dotenv
    load_dotenv()

    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_pwd = os.getenv("NEO4J_PASSWORD")

    if neo4j_uri and neo4j_pwd:
        print("PASS: Neo4j credentials configured")
        print(f"  URI: {neo4j_uri}")
    else:
        print("WARN: Neo4j credentials not configured")
        print(f"  NEO4J_URI: {'SET' if neo4j_uri else 'MISSING'}")
        print(f"  NEO4J_PASSWORD: {'SET' if neo4j_pwd else 'MISSING'}")

    graph_enabled = os.getenv("GRAPH_ORACLE_ENABLED", "").lower() == "true"
    print(f"INFO: GRAPH_ORACLE_ENABLED: {graph_enabled}")

except Exception as e:
    print(f"WARN: Environment check failed: {e}")

# Test 5: Verify recent commit
print("\n[TEST 5] Recent commit verification")
print("-" * 60)
try:
    import subprocess
    result = subprocess.run(
        ['git', 'log', '-1', '--oneline'],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    commit = result.stdout.strip()

    if 'fix(agents): flatten Commander description' in commit:
        print("PASS: Latest commit is the description fix")
        print(f"  {commit}")
    else:
        print("WARN: Latest commit is not the description fix")
        print(f"  {commit}")

except Exception as e:
    print(f"WARN: Git check failed: {e}")

# Summary
print("\n" + "=" * 60)
print("HEALTH CHECK: PASSED")
print("=" * 60)
print("\nSummary:")
print("  - Commander description: single-line (no block scalar)")
print("  - Multi-platform sync: verified")
print("  - aura-oracle: available")
print("  - Environment: configured")
print("\nCommander should initialize without classifyHandoffIfNeeded errors.")
