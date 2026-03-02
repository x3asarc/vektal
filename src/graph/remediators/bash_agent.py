from src.graph.remediators.code_remediator import CodeRemediator
from src.assistant.governance.kill_switch import check_kill_switch
from typing import Dict, List, Any
import subprocess
import shutil
import logging

logger = logging.getLogger(__name__)

class BashAgent(CodeRemediator):
    """Automated infrastructure remediation via bash commands."""

    ALLOWED_COMMANDS = {
        'redis_restart': ['docker', 'restart', 'redis'],
        'docker_restart': ['docker', 'restart', 'backend'],
        'cache_clear': ['docker', 'exec', 'redis', 'redis-cli', 'FLUSHDB'],
        'pool_tune': None  # Requires config file edit + restart
    }

    @property
    def service_name(self) -> str:
        return "bash_agent"

    def detect(self, parameters: Dict) -> bool:
        """Detect infrastructure failures."""
        error_type = parameters.get('error_type', '')
        error_message = parameters.get('error_message', '').lower()
        
        is_infra_error = error_type in [
            'ConnectionError', 'docker.errors.APIError', 'PoolError', 'OperationalError'
        ]
        has_infra_keyword = any(kw in error_message for kw in ['redis', 'docker', 'connection refused', 'pool'])
        
        return is_infra_error and has_infra_keyword

    def remediate(self, parameters: Dict) -> Dict:
        """Execute infrastructure remediation."""
        # Check kill-switch (Phase 13 integration)
        if not self._is_auto_apply_enabled():
            return {
                'success': False,
                'action': 'kill_switch_active',
                'message': 'Infrastructure auto-apply disabled by kill-switch'
            }

        # Determine command
        error_msg = parameters.get('error_message', '').lower()
        if 'redis' in error_msg:
            command = self.ALLOWED_COMMANDS['redis_restart']
            description = 'Restart Redis container'
        elif 'docker' in error_msg:
            command = self.ALLOWED_COMMANDS['docker_restart']
            description = 'Restart backend container'
        else:
            return {'success': False, 'action': 'unknown_infra_error', 'message': f"No allowlisted command for: {error_msg}"}

        # Validate in sandbox (dry-run)
        sandbox_result = self._validate_bash_command(command)
        if not sandbox_result['safe']:
            return {
                'success': False,
                'action': 'sandbox_blocked',
                'reason': sandbox_result['reason']
            }

        # Execute (Phase 15.2 only - for now, create approval)
        # Note: In Phase 15.1, we always return approval_required for safety
        return {
            'success': True,
            'action': 'approval_required',  # Phase 15.1: Still requires approval
            'command': ' '.join(command),
            'description': description,
            'sandbox_validated': True,
            'sandbox_probe': sandbox_result.get('probe')
        }

    def _validate_bash_command(self, command: List[str]) -> Dict:
        """Validate bash command safety + executable preflight probe."""
        if not command:
            return {'safe': False, 'reason': 'empty_command'}
            
        # Check against allowlist
        cmd_str = ' '.join(command)
        is_allowlisted = False
        for allowed in self.ALLOWED_COMMANDS.values():
            if allowed and cmd_str == ' '.join(allowed):
                is_allowlisted = True
                break
                
        if not is_allowlisted:
            return {'safe': False, 'reason': 'command_not_allowlisted'}

        # No destructive flags
        destructive_flags = ['--force', '-f', 'rm', 'delete', 'drop']
        if any(flag in cmd_str for flag in destructive_flags):
            return {'safe': False, 'reason': 'destructive_command'}

        if shutil.which(command[0]) is None:
            return {'safe': False, 'reason': 'command_binary_missing'}

        probe = self._run_sandbox_probe(command)
        if not probe.get('ok'):
            return {'safe': False, 'reason': probe.get('reason', 'probe_failed')}

        return {'safe': True, 'probe': probe}

    def _run_sandbox_probe(self, command: List[str]) -> Dict[str, Any]:
        """
        Execute a read-only probe command to verify runtime safety preconditions.
        """
        try:
            if command[:2] == ['docker', 'restart']:
                probe_cmd = ['docker', 'ps', '--format', '{{.Names}}']
            elif command[:3] == ['docker', 'exec', 'redis']:
                probe_cmd = ['docker', 'exec', 'redis', 'redis-cli', 'PING']
            else:
                probe_cmd = [command[0], '--help']

            result = subprocess.run(
                probe_cmd,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            if result.returncode != 0:
                stderr = (result.stderr or '').strip().lower()
                return {'ok': False, 'reason': f'probe_failed:{stderr[:120]}'}

            return {
                'ok': True,
                'probe_command': ' '.join(probe_cmd),
                'stdout_preview': (result.stdout or '').strip()[:120]
            }
        except Exception as exc:
            return {'ok': False, 'reason': f'probe_exception:{exc}'}

    def _is_auto_apply_enabled(self) -> bool:
        """
        Fail-safe gate check: any lookup failure keeps auto-apply blocked.
        """
        try:
            return bool(check_kill_switch('infrastructure_auto_apply'))
        except Exception as exc:
            logger.warning("Kill-switch lookup failed; failing closed: %s", exc)
            return False

    def describe(self) -> str:
        return "Infrastructure bash agent (Redis, Docker, cache)"
