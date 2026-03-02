from unittest.mock import MagicMock, patch

from src.graph.remediators.bash_agent import BashAgent


def test_bash_agent_detection():
    agent = BashAgent()

    assert agent.detect(
        {"error_type": "ConnectionError", "error_message": "redis connection refused"}
    ) is True
    assert agent.detect(
        {"error_type": "docker.errors.APIError", "error_message": "docker daemon down"}
    ) is True
    assert agent.detect({"error_type": "ValueError", "error_message": "bad value"}) is False


@patch("src.graph.remediators.bash_agent.BashAgent._run_sandbox_probe")
@patch("src.graph.remediators.bash_agent.shutil.which")
@patch("src.graph.remediators.bash_agent.check_kill_switch")
def test_bash_agent_remediate_success(mock_check, mock_which, mock_probe):
    mock_check.return_value = True
    mock_which.return_value = "docker"
    mock_probe.return_value = {"ok": True, "probe_command": "docker ps"}

    agent = BashAgent()
    result = agent.remediate(
        {"error_type": "ConnectionError", "error_message": "redis connection refused"}
    )

    assert result["success"] is True
    assert result["action"] == "approval_required"
    assert "docker restart redis" in result["command"]
    assert result["sandbox_validated"] is True


@patch("src.graph.remediators.bash_agent.check_kill_switch")
def test_bash_agent_kill_switch(mock_check):
    mock_check.return_value = False
    agent = BashAgent()
    result = agent.remediate(
        {"error_type": "ConnectionError", "error_message": "redis connection refused"}
    )
    assert result["success"] is False
    assert result["action"] == "kill_switch_active"


@patch("src.graph.remediators.bash_agent.BashAgent._run_sandbox_probe")
@patch("src.graph.remediators.bash_agent.shutil.which")
def test_bash_agent_command_validation(mock_which, mock_probe):
    agent = BashAgent()
    mock_which.return_value = "docker"
    mock_probe.return_value = {"ok": True, "probe_command": "docker ps"}

    assert agent._validate_bash_command(["docker", "restart", "redis"])["safe"] is True
    assert agent._validate_bash_command(["rm", "-rf", "/"])["safe"] is False
    assert agent._validate_bash_command(["docker", "run", "malicious"])["safe"] is False
    assert (
        agent._validate_bash_command(["docker", "restart", "redis", "--force"])["safe"]
        is False
    )


@patch("src.graph.remediators.bash_agent.BashAgent._run_sandbox_probe")
@patch("src.graph.remediators.bash_agent.shutil.which")
def test_bash_agent_probe_failure_blocks_command(mock_which, mock_probe):
    mock_which.return_value = "docker"
    mock_probe.return_value = {"ok": False, "reason": "probe_failed"}
    agent = BashAgent()
    result = agent._validate_bash_command(["docker", "restart", "redis"])
    assert result["safe"] is False
    assert result["reason"] == "probe_failed"
