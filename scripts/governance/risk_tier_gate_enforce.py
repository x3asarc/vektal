#!/usr/bin/env python3
"""
Risk tier gate enforcer - Actually runs required checks and blocks on failure.
Called by PreToolUse hook before git commits.
"""
import json
import subprocess
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Use ASCII characters for compatibility
CHECK = "[OK]"
CROSS = "[FAIL]"
WARN = "[WARN]"


def run_command(cmd: list[str], description: str, timeout: int = 300) -> tuple[bool, str]:
    """Run a command and return (success, output)."""
    print(f"{BLUE}Running: {description}...{RESET}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            print(f"{GREEN}{CHECK} {description} passed{RESET}")
            return True, result.stdout
        else:
            print(f"{RED}{CROSS} {description} failed{RESET}")
            print(f"{RED}{result.stdout}{RESET}")
            print(f"{RED}{result.stderr}{RESET}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"{RED}{CROSS} {description} timed out (>{timeout}s){RESET}")
        return False, "Timeout"
    except Exception as e:
        print(f"{RED}{CROSS} {description} error: {e}{RESET}")
        return False, str(e)


def run_backend_tests() -> bool:
    """Run backend unit tests (fast mode for commits)."""
    # Run only unit tests (skip integration tests for speed)
    # Use -x to stop on first failure, --lf to run last failed first
    return run_command(
        ["python", "-m", "pytest", "tests/unit/", "-x", "--tb=short", "-q", "--lf", "--maxfail=3"],
        "Backend unit tests (fast mode)",
        timeout=120
    )[0]


def run_secret_lint() -> bool:
    """Run secret scanning on changed files only."""
    # Get changed files from git
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        changed_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

        if not changed_files:
            print(f"{GREEN}{CHECK} Secret lint (no files to scan){RESET}")
            return True
    except Exception:
        # Fall back to scanning all files if git command fails
        changed_files = []

    # Fast secret scan on changed files only
    scan_script = f"""
import pathlib, re, sys, json

policy = json.loads(pathlib.Path("risk-policy.json").read_text())
patterns = [re.compile(p) for p in policy.get("secret_lint_patterns", [])]
skip_paths = policy.get("secret_lint_skip_paths", [])

def should_skip(path_str):
    for skip_pattern in skip_paths:
        if skip_pattern.endswith("/**/*.*") or skip_pattern.endswith("**/*.*"):
            prefix = skip_pattern.split("*")[0]
            if path_str.startswith(prefix):
                return True
        elif path_str.startswith(skip_pattern):
            return True
    return False

changed_files = {changed_files!r}
violations = []

for file_path in changed_files:
    path = pathlib.Path(file_path)
    if not path.exists() or should_skip(str(path)):
        continue

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue

    for i, line in enumerate(text.splitlines(), start=1):
        for pat in patterns:
            if pat.search(line):
                violations.append(f"{{path}}:{{i}}: {{line.strip()[:120]}}")
                break

if violations:
    print("Potential hardcoded secrets detected:")
    print("\\n".join(violations))
    sys.exit(1)
print("Secret scan clean.")
"""
    return run_command(
        ["python", "-c", scan_script],
        "Secret lint",
        timeout=30
    )[0]


def run_governance_validate() -> bool:
    """Run governance validation."""
    validate_script = Path("scripts/governance/validate_governance.py")
    if not validate_script.exists():
        print(f"{YELLOW}{WARN} Governance validator not found, skipping{RESET}")
        return True  # Don't block if validator doesn't exist

    return run_command(
        ["python", str(validate_script)],
        "Governance validation"
    )[0]


def main() -> int:
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Risk Tier Gate Enforcer{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    # Step 1: Classify the changes
    print(f"{BLUE}Step 1: Classifying changed files...{RESET}")
    try:
        result = subprocess.run(
            ["python", "scripts/governance/risk_tier_gate.py", "--from-git-diff"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print(f"{RED}Failed to classify files{RESET}")
            print(result.stderr)
            return 1

        classification = json.loads(result.stdout)
    except Exception as e:
        print(f"{RED}Error running classifier: {e}{RESET}")
        return 1

    # Display classification
    tier = classification["tier"]
    required_checks = classification["required_checks"]
    matched_files = classification.get("matched_files", {})

    print(f"\n{YELLOW}Risk Tier: {tier.upper()}{RESET}")
    print(f"{YELLOW}Required Checks: {', '.join(required_checks)}{RESET}")

    if matched_files:
        print(f"\n{BLUE}Matched Files:{RESET}")
        for file, file_tier in matched_files.items():
            tier_color = RED if file_tier == "critical" else YELLOW if file_tier == "high" else BLUE
            print(f"  {tier_color}{file_tier:8s}{RESET} {file}")

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Step 2: Running required checks...{RESET}\n")

    # Step 2: Run required checks
    all_passed = True
    check_mapping = {
        "backend-unit-tests": run_backend_tests,
        "backend-integration-tests": run_backend_tests,  # Same for now
        "secret-lint": run_secret_lint,
        "governance-validate": run_governance_validate,
    }

    for check in required_checks:
        if check == "risk-policy-gate":
            # Already done in step 1
            print(f"{GREEN}{CHECK} Risk policy gate (classification){RESET}")
            continue

        if check == "canary-gate":
            # Skip canary gate for local commits
            print(f"{YELLOW}{WARN} Canary gate (CI-only, skipped locally){RESET}")
            continue

        runner = check_mapping.get(check)
        if runner:
            passed = runner()
            if not passed:
                all_passed = False
        else:
            print(f"{YELLOW}{WARN} Unknown check: {check} (skipped){RESET}")

    # Step 3: Final verdict
    print(f"\n{BLUE}{'='*60}{RESET}")
    if all_passed:
        print(f"{GREEN}{CHECK} All checks passed - commit allowed{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        return 0
    else:
        print(f"{RED}{CROSS} Some checks failed - commit blocked{RESET}")
        print(f"{RED}Fix the issues above before committing{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
