#!/usr/bin/env python
"""
CI governance gate for graph integration.

Provides binary GREEN/RED output with emission hook validation,
import checks, and contract test execution.

Phase 13.2 - Oracle Framework Reuse
"""

import argparse
import sys
import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional


# ===========================================
# Required Emission Hook Checks
# ===========================================

REQUIRED_EMISSION_HOOKS = [
    ('src/assistant/governance/verification_oracle.py', 'emit_episode'),
    ('src/api/v1/chat/approvals.py', 'emit_episode'),
    ('src/tasks/enrichment.py', 'emit_episode'),
]


def check_emission_hooks(verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Verify all required emission hooks are present in source files.

    Args:
        verbose: Whether to print detailed output

    Returns:
        Tuple of (all_found: bool, missing_hooks: List[str])
    """
    project_root = Path(__file__).parent.parent.parent
    missing = []
    found = []

    for file_path, pattern in REQUIRED_EMISSION_HOOKS:
        full_path = project_root / file_path

        if not full_path.exists():
            missing.append(f"{file_path} (file not found)")
            continue

        content = full_path.read_text(encoding='utf-8')

        if pattern in content:
            found.append(file_path)
            if verbose:
                print(f"  {file_path}: FOUND")
        else:
            missing.append(f"{file_path} (pattern '{pattern}' not found)")
            if verbose:
                print(f"  {file_path}: MISSING")

    return len(missing) == 0, missing


# ===========================================
# Import Checks
# ===========================================

REQUIRED_IMPORTS = [
    'src.core.graphiti_client',
    'src.core.synthex_entities',
    'src.tasks.graphiti_sync',
    'src.assistant.governance.graph_oracle_adapter',
]


def check_imports(verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Verify all graph modules import without error.

    Args:
        verbose: Whether to print detailed output

    Returns:
        Tuple of (all_ok: bool, failed_imports: List[str])
    """
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    failed = []
    succeeded = []

    for module_name in REQUIRED_IMPORTS:
        try:
            __import__(module_name)
            succeeded.append(module_name)
            if verbose:
                print(f"  {module_name}: OK")
        except Exception as e:
            failed.append(f"{module_name} ({e})")
            if verbose:
                print(f"  {module_name}: FAILED ({e})")

    return len(failed) == 0, failed


# ===========================================
# Contract Test Runner
# ===========================================

CONTRACT_TESTS = [
    'tests/core/test_graphiti_client_contract.py',
    'tests/core/test_synthex_entities.py',
    'tests/tasks/test_graphiti_sync_contract.py',
    'tests/api/test_graph_oracle_adapter_contract.py',
]


def run_contract_tests(verbose: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Execute contract test suite.

    Args:
        verbose: Whether to show detailed test output

    Returns:
        Tuple of (all_passed: bool, error_message: Optional[str])
    """
    project_root = Path(__file__).parent.parent.parent

    # Build pytest command
    cmd = [
        sys.executable,
        '-m',
        'pytest',
        *CONTRACT_TESTS,
        '-q',  # Quiet mode
    ]

    if verbose:
        cmd.append('-v')  # Verbose mode if requested

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120
        )

        if verbose:
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

        return result.returncode == 0, None if result.returncode == 0 else result.stdout

    except subprocess.TimeoutExpired:
        return False, "Test execution timed out after 120s"
    except Exception as e:
        return False, f"Test execution failed: {e}"


# ===========================================
# Main Gate Logic
# ===========================================

def print_header(title: str):
    """Print section header."""
    print(f"\n[Graph Gate] {title}...")


def run_gate(
    check_hooks: bool = True,
    check_module_imports: bool = True,
    run_tests: bool = True,
    verbose: bool = False
) -> bool:
    """
    Run graph integration governance gate.

    Args:
        check_hooks: Whether to check emission hooks
        check_module_imports: Whether to check imports
        run_tests: Whether to run contract tests
        verbose: Whether to show detailed output

    Returns:
        bool: True if all checks pass (GREEN), False otherwise (RED)
    """
    all_passed = True

    # Emission hook check
    if check_hooks:
        print_header("Emission Hook Check")
        hooks_ok, missing = check_emission_hooks(verbose=verbose)

        if not hooks_ok:
            print(f"  FAILED: {len(missing)} missing hooks")
            for item in missing:
                print(f"    - {item}")
            all_passed = False
        else:
            print("  PASSED: All emission hooks found")

    # Import check
    if check_module_imports:
        print_header("Import Check")
        imports_ok, failed = check_imports(verbose=verbose)

        if not imports_ok:
            print(f"  FAILED: {len(failed)} import errors")
            for item in failed:
                print(f"    - {item}")
            all_passed = False
        else:
            print("  PASSED: All modules import successfully")

    # Contract tests
    if run_tests:
        print_header("Contract Tests")
        tests_ok, error_msg = run_contract_tests(verbose=verbose)

        if not tests_ok:
            print("  FAILED: Contract tests did not pass")
            if error_msg:
                print(f"  Error: {error_msg}")
            all_passed = False
        else:
            print("  PASSED: All contract tests passed")

    # Print verdict
    print_header("VERDICT")
    if all_passed:
        print("  \033[92mGREEN\033[0m - Graph integration ready")
        return True
    else:
        print("  \033[91mRED\033[0m - Graph integration has issues")
        return False


# ===========================================
# CLI Entry Point
# ===========================================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CI governance gate for graph integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full gate
  python scripts/governance/graph_gate.py

  # Check only emission hooks
  python scripts/governance/graph_gate.py --check-emission-hooks

  # Run only tests
  python scripts/governance/graph_gate.py --run-tests

  # Dry run (skip tests)
  python scripts/governance/graph_gate.py --dry-run

  # Verbose output
  python scripts/governance/graph_gate.py --verbose
        """
    )

    parser.add_argument(
        '--check-emission-hooks',
        action='store_true',
        help='Only run emission hook check'
    )

    parser.add_argument(
        '--run-tests',
        action='store_true',
        help='Only run contract tests'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Skip tests, only run static checks'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    # Determine what to run
    if args.check_emission_hooks:
        # Only emission hooks
        success = run_gate(
            check_hooks=True,
            check_module_imports=False,
            run_tests=False,
            verbose=args.verbose
        )
    elif args.run_tests:
        # Only tests
        success = run_gate(
            check_hooks=False,
            check_module_imports=False,
            run_tests=True,
            verbose=args.verbose
        )
    elif args.dry_run:
        # Static checks only (no tests)
        success = run_gate(
            check_hooks=True,
            check_module_imports=True,
            run_tests=False,
            verbose=args.verbose
        )
    else:
        # Full gate
        success = run_gate(
            check_hooks=True,
            check_module_imports=True,
            run_tests=True,
            verbose=args.verbose
        )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
