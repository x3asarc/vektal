import pytest
import json
from unittest.mock import MagicMock, patch
from src.graph.fix_generator import FixGenerator
from src.graph.remediators.llm_remediator import LLMRemediator

@pytest.fixture
def mock_llm_client():
    with patch("src.graph.fix_generator.get_llm_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_session_primer():
    with patch("src.graph.fix_generator.SessionPrimer") as mock:
        primer = MagicMock()
        primer.load_session_context.return_value = "Mock Context"
        yield primer

@pytest.fixture
def mock_remedy_template():
    with patch("src.graph.fix_generator.RemedyTemplate") as mock:
        yield mock

@pytest.fixture
def mock_sandbox():
    with patch("src.graph.remediators.llm_remediator.SandboxRunner") as mock:
        sandbox = MagicMock()
        mock.return_value = sandbox
        yield sandbox

def test_fix_generator_template_match(mock_remedy_template):
    # Setup template match
    template = MagicMock()
    template.confidence = 0.95
    template.template_id = "tmpl_123"
    template.remedy_payload = json.dumps({"src/test.py": "fixed content"})
    template.description = "Template fix"
    mock_remedy_template.query_relevant.return_value = [template]

    gen = FixGenerator()
    fix, conf = gen.generate_fix(
        error_type="TimeoutError",
        error_message="timeout",
        affected_module="src/test.py",
        traceback="...",
        classification_evidence={}
    )

    assert fix["type"] == "template"
    assert fix["template_id"] == "tmpl_123"
    assert fix["changed_files"] == {"src/test.py": "fixed content"}
    assert conf == 0.95

def test_fix_generator_llm_fallback(mock_remedy_template, mock_llm_client, mock_session_primer):
    # No template match
    mock_remedy_template.query_relevant.return_value = []
    
    # LLM response
    mock_llm_client.complete.return_value = json.dumps({
        "changed_files": {"src/test.py": "llm fixed content"},
        "description": "LLM fix",
        "confidence": 0.85
    })

    gen = FixGenerator()
    fix, conf = gen.generate_fix(
        error_type="ValueError",
        error_message="bad value",
        affected_module="src/test.py",
        traceback="...",
        classification_evidence={}
    )

    assert fix["type"] == "llm_generated"
    assert fix["changed_files"] == {"src/test.py": "llm fixed content"}
    assert conf == 0.85
    assert "google/gemini-2.0-flash-001" in fix["llm_model"]

def test_fix_generator_model_selection():
    gen = FixGenerator()
    
    # Small traceback -> Flash
    model_small = gen._select_model("src/tasks/enrichment.py", 100)
    assert "flash" in model_small.lower()
    
    # Large traceback -> Sonnet
    model_large = gen._select_model("src/tasks/enrichment.py", 1500)
    assert "sonnet" in model_large.lower()
    
    # Config module -> Flash even if large? (Actually logic says 'config' in module OR len < 500)
    model_config = gen._select_model("src/config/settings.py", 2000)
    assert "flash" in model_config.lower()

def test_llm_remediator_auto_apply(mock_llm_client, mock_sandbox, mock_remedy_template):
    # Mock fix generation (High confidence)
    mock_remedy_template.query_relevant.return_value = []
    mock_llm_client.complete.return_value = json.dumps({
        "changed_files": {"src/test.py": "fix"},
        "description": "fix",
        "confidence": 0.95
    })
    
    # Mock sandbox (GREEN)
    mock_sandbox.run_verification.return_value = {
        "verdict": "GREEN",
        "run_id": "run_123"
    }

    remediator = LLMRemediator()
    result = remediator.remediate({
        "error_type": "SyntaxError",
        "error_message": "invalid",
        "affected_module": "src/test.py"
    })

    assert result["success"] is True
    assert result["action"] == "auto_apply_ready"
    assert result["confidence"] == 0.95

def test_llm_remediator_approval_required(mock_llm_client, mock_sandbox, mock_remedy_template):
    # Mock fix generation (Medium confidence)
    mock_remedy_template.query_relevant.return_value = []
    mock_llm_client.complete.return_value = json.dumps({
        "changed_files": {"src/test.py": "fix"},
        "description": "fix",
        "confidence": 0.8
    })
    
    # Mock sandbox (GREEN)
    mock_sandbox.run_verification.return_value = {
        "verdict": "GREEN",
        "run_id": "run_456"
    }

    remediator = LLMRemediator()
    result = remediator.remediate({
        "error_type": "TypeError",
        "error_message": "type error",
        "affected_module": "src/test.py"
    })

    assert result["success"] is True
    assert result["action"] == "approval_required"
    assert result["confidence"] == 0.8

def test_llm_remediator_blocked(mock_llm_client, mock_sandbox, mock_remedy_template):
    # Mock fix generation
    mock_remedy_template.query_relevant.return_value = []
    mock_llm_client.complete.return_value = json.dumps({
        "changed_files": {"src/test.py": "fix"},
        "description": "fix",
        "confidence": 0.8
    })
    
    # Mock sandbox (RED)
    mock_sandbox.run_verification.return_value = {
        "verdict": "RED",
        "run_id": "run_789"
    }

    remediator = LLMRemediator()
    result = remediator.remediate({
        "error_type": "AttributeError",
        "error_message": "no attr",
        "affected_module": "src/test.py"
    })

    assert result["success"] is False
    assert result["action"] == "blocked"
