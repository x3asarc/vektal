"""
Integration test for the Universal Sandbox.
Verifies syntax and unit test gates.
"""

import asyncio
import logging
import os
import shutil
import json
from pathlib import Path
from src.graph.sandbox_verifier import SandboxRunner

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

async def test_sandbox_success():
    """Test a successful verification run."""
    runner = SandboxRunner()
    
    # Define a mock fix that passes
    fix_payload = {
        "files": {
            "src/core/sandbox_success.py": "def add(a, b):\n    return a + b\n",
            "tests/unit/test_sandbox_success.py": (
                "from src.core.sandbox_success import add\n"
                "def test_add():\n"
                "    assert add(1, 2) == 3\n"
            )
        },
        "tests": ["tests/unit/test_sandbox_success.py"]
    }
    
    logger.info("🧪 [IntegrationTest] Starting success run...")
    result = await runner.verify_fix(fix_payload)
    
    logger.info(f"Outcome: {'SUCCESS' if result.success else 'FAILED'}")
    for gate in result.gates:
        logger.info(f"  Gate {gate.name}: {gate.status} - {gate.message or ''}")
    
    assert result.success, "Sandbox verification should have succeeded"
    assert result.gates[0].status == "PASS", "Syntax gate should pass"
    assert result.gates[2].status == "PASS", "Unit test gate should pass"

async def test_sandbox_syntax_fail():
    """Test a syntax failure."""
    runner = SandboxRunner()
    
    # Define a mock fix with syntax error
    fix_payload = {
        "files": {
            "src/core/sandbox_fail.py": "def invalid syntax here..."
        }
    }
    
    logger.info("🧪 [IntegrationTest] Starting syntax failure run...")
    result = await runner.verify_fix(fix_payload)
    
    logger.info(f"Outcome: {'SUCCESS' if result.success else 'FAILED'}")
    for gate in result.gates:
        logger.info(f"  Gate {gate.name}: {gate.status} - {gate.message or ''}")
    
    assert not result.success, "Sandbox verification should have failed"
    assert result.gates[0].status == "FAIL", "Syntax gate should fail"

async def main():
    try:
        await test_sandbox_success()
        await test_sandbox_syntax_fail()
        logger.info("✅ [IntegrationTest] All sandbox tests passed!")
    except Exception as e:
        logger.error(f"❌ [IntegrationTest] Tests failed: {e}")
        # Cleanup
        if os.path.exists(".sandbox"):
             shutil.rmtree(".sandbox", ignore_errors=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
