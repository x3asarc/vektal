"""
Tests for Typer CLI commands.
"""

import pytest
import sys
from pathlib import Path
from typer.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cli.main import app

runner = CliRunner()


def test_help_shows_subcommands():
    """Test that main help shows products and search subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "products" in result.stdout
    assert "search" in result.stdout
    assert "Unified CLI for Shopify product management" in result.stdout


def test_products_help():
    """Test that products subcommand help shows available commands."""
    result = runner.invoke(app, ["products", "--help"])
    assert result.exit_code == 0
    assert "update-sku" in result.stdout
    assert "analyze" in result.stdout
    assert "process" in result.stdout


def test_search_help():
    """Test that search subcommand help shows available commands."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "by-sku" in result.stdout
    assert "by-title" in result.stdout
    assert "by-handle" in result.stdout


def test_update_sku_requires_sku():
    """Test that update-sku command requires a SKU argument."""
    result = runner.invoke(app, ["products", "update-sku"])
    # Should fail without SKU argument
    assert result.exit_code != 0


def test_search_by_sku_dry_run():
    """Test that search by-sku command can run in dry-run mode (structure test)."""
    result = runner.invoke(app, ["search", "by-sku", "TEST-SKU", "--dry-run"])
    # May fail if no actual connection - that's OK for structure test
    # We're just verifying the command exists and accepts arguments
    assert result.exit_code in [0, 1]  # Either succeeds or fails gracefully


def test_analyze_requires_identifier():
    """Test that analyze command requires at least one identifier."""
    result = runner.invoke(app, ["products", "analyze"])
    # Should fail without any identifier
    assert result.exit_code != 0


def test_process_requires_csv():
    """Test that process command requires a CSV file argument."""
    result = runner.invoke(app, ["products", "process"])
    # Should fail without CSV file
    assert result.exit_code != 0


def test_cli_structure():
    """Test the overall CLI structure is correct."""
    # Main app exists
    assert app is not None

    # Has commands
    result = runner.invoke(app, ["--help"])
    assert "products" in result.stdout
    assert "search" in result.stdout

    # Products has subcommands
    result = runner.invoke(app, ["products", "--help"])
    assert "update-sku" in result.stdout
    assert "analyze" in result.stdout
    assert "process" in result.stdout

    # Search has subcommands
    result = runner.invoke(app, ["search", "--help"])
    assert "by-sku" in result.stdout
    assert "by-title" in result.stdout
    assert "by-handle" in result.stdout
