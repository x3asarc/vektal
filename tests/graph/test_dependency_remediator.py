"""Tests for dependency remediator."""

import pytest
from unittest.mock import patch, MagicMock
from src.graph.remediators.dependency_remediator import DependencyRemediator


@pytest.mark.asyncio
async def test_validate_environment_success():
    """Test that pip validation succeeds when pip is available."""
    remediator = DependencyRemediator()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = await remediator.validate_environment()
        assert result is True


@pytest.mark.asyncio
async def test_validate_environment_failure():
    """Test that pip validation fails when pip is unavailable."""
    remediator = DependencyRemediator()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = await remediator.validate_environment()
        assert result is False


@pytest.mark.asyncio
async def test_extract_module_from_error_message():
    """Test module name extraction from various error formats."""
    remediator = DependencyRemediator()

    # Test "Module 'xxx' not found" pattern
    assert remediator._extract_module_name("Module 'sentry_sdk' not found", "") == "sentry_sdk"

    # Test "No module named 'xxx'" pattern
    assert remediator._extract_module_name("No module named 'graphiti_core'", "") == "graphiti_core"

    # Test ModuleNotFoundError pattern
    assert remediator._extract_module_name("ModuleNotFoundError: neo4j", "") == "neo4j"

    # Test fallback to affected_module
    assert remediator._extract_module_name("", "typer") == "typer"


@pytest.mark.asyncio
async def test_package_mapping():
    """Test that package names are correctly mapped."""
    remediator = DependencyRemediator()

    # Test known mappings
    assert remediator.PACKAGE_MAP["sentry_sdk"] == "sentry-sdk"
    assert remediator.PACKAGE_MAP["graphiti_core"] == "graphiti-core"
    assert remediator.PACKAGE_MAP["flask_openapi3"] == "flask-openapi3"
    assert remediator.PACKAGE_MAP["requests_mock"] == "requests-mock"


@pytest.mark.asyncio
async def test_install_success():
    """Test successful dependency installation and verification."""
    remediator = DependencyRemediator()

    params = {
        "error_message": "Module 'sentry_sdk' not found",
        "affected_module": "src.core.sentry",
    }

    with patch("subprocess.run") as mock_run:
        # Mock successful install
        install_result = MagicMock(returncode=0, stdout="Successfully installed")
        # Mock successful import
        verify_result = MagicMock(returncode=0)

        mock_run.side_effect = [install_result, verify_result]

        result = await remediator.diagnose_and_fix(params)

        assert result.success is True
        assert "sentry-sdk" in result.message
        assert "pip_install_sentry-sdk" in result.actions_taken
        assert "install_success" in result.actions_taken
        assert "import_verification_success" in result.actions_taken


@pytest.mark.asyncio
async def test_install_failure():
    """Test handling of failed installation."""
    remediator = DependencyRemediator()

    params = {
        "error_message": "Module 'fake_module' not found",
        "affected_module": "",
    }

    with patch("subprocess.run") as mock_run:
        # Mock failed install
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="ERROR: Could not find a version that satisfies the requirement"
        )

        result = await remediator.diagnose_and_fix(params)

        assert result.success is False
        assert "Failed to install" in result.message
        assert "install_failed" in result.actions_taken
        assert result.error_details is not None


@pytest.mark.asyncio
async def test_install_success_import_failure():
    """Test when installation succeeds but import still fails."""
    remediator = DependencyRemediator()

    params = {
        "error_message": "Module 'broken_module' not found",
        "affected_module": "",
    }

    with patch("subprocess.run") as mock_run:
        # Mock successful install but failed import
        install_result = MagicMock(returncode=0)
        verify_result = MagicMock(returncode=1, stderr="ImportError")

        mock_run.side_effect = [install_result, verify_result]

        result = await remediator.diagnose_and_fix(params)

        assert result.success is False
        assert "import still fails" in result.message
        assert "install_success" in result.actions_taken
        assert "import_verification_failed" in result.actions_taken


@pytest.mark.asyncio
async def test_no_module_name_extracted():
    """Test handling when module name cannot be extracted."""
    remediator = DependencyRemediator()

    params = {
        "error_message": "Some random error",
        "affected_module": "",
    }

    result = await remediator.diagnose_and_fix(params)

    assert result.success is False
    assert "Could not extract module name" in result.message
    assert "module_extraction_failed" in result.actions_taken


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test handling of installation timeout."""
    remediator = DependencyRemediator()

    params = {
        "error_message": "Module 'slow_package' not found",
        "affected_module": "",
    }

    with patch("subprocess.run") as mock_run:
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("pip install", 120)

        result = await remediator.diagnose_and_fix(params)

        assert result.success is False
        assert "timeout" in result.message.lower()
        assert "install_timeout" in result.actions_taken


@pytest.mark.asyncio
async def test_service_name_and_description():
    """Test remediator metadata."""
    remediator = DependencyRemediator()

    assert remediator.service_name == "dependencies"
    assert "Python dependencies" in remediator.description
