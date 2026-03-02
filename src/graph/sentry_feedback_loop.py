from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from src.graph.template_extractor import TemplateExtractor
from src.models.sandbox_runs import SandboxRun, SandboxVerdict
from src.models import db
import logging

logger = logging.getLogger(__name__)

class SentryFeedbackLoop:
    """Validates remediation efficacy by checking Sentry issue state."""

    def __init__(self, sentry_client):
        self.sentry_client = sentry_client
        self.template_extractor = TemplateExtractor()

    def validate_pending_remediations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Check all pending remediations from last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Query SandboxRuns that were successful in sandbox
        pending_runs = SandboxRun.query.filter(
            SandboxRun.completed_at >= cutoff,
            SandboxRun.verdict == SandboxVerdict.GREEN
        ).all()

        results = []
        for run in pending_runs:
            if not run.failure_fingerprint:
                continue

            # Extract Sentry issue ID from fingerprint
            sentry_issue_id = self._extract_issue_id(run.failure_fingerprint)
            if not sentry_issue_id:
                continue

            # Query Sentry for current issue state
            issue = self.sentry_client.get_issue(sentry_issue_id)
            if issue.get('status') == 'unknown':
                continue

            # Validate: Issue should be resolved AND have no new events after remediation
            is_resolved = issue.get('status') == 'resolved'
            # Activity after remediation check
            activity = issue.get('activity', [])
            has_new_events = False
            
            if activity:
                # In a real Sentry issue, activity objects have timestamps
                # We check if any activity (re-opened, new event) happened after run.completed_at
                for act in activity:
                    act_date_str = act.get('dateCreated')
                    if act_date_str:
                        act_date = datetime.fromisoformat(act_date_str.replace('Z', '+00:00'))
                        if act_date > run.completed_at:
                            has_new_events = True
                            break

            if is_resolved and not has_new_events:
                # Success - promote to template
                logger.info(f"Remediation successful for {sentry_issue_id}")
                self._promote_to_template(run)
                results.append({
                    'run_id': run.run_id,
                    'status': 'validated',
                    'sentry_issue_id': sentry_issue_id
                })
            elif has_new_events:
                # Failure - same error recurring
                logger.warning(f"Remediation failed for {sentry_issue_id} - issue recurring")
                self._mark_failed(run)
                results.append({
                    'run_id': run.run_id,
                    'status': 'failed',
                    'sentry_issue_id': sentry_issue_id,
                    'reason': 'issue_recurring'
                })
            else:
                # Pending - wait longer (not yet resolved but no new events)
                results.append({
                    'run_id': run.run_id,
                    'status': 'pending',
                    'sentry_issue_id': sentry_issue_id
                })

        return results

    def _promote_to_template(self, run: SandboxRun):
        """Promote validated fix to template library."""
        try:
            # changed_files in SandboxRun is JSON/dict
            changed_files = run.changed_files if isinstance(run.changed_files, dict) else {}
            
            template_id = self.template_extractor.extract_and_promote(
                fix_payload={
                    'changed_files': changed_files,
                    'description': f"Validated fix for {run.failure_fingerprint}"
                },
                confidence=float(run.confidence or 0.9),
                fingerprint=run.failure_fingerprint
            )
            logger.info(f"Promoted run {run.run_id} to template {template_id}")
        except Exception as e:
            logger.error(f"Failed to promote run {run.run_id}: {e}")

    def _mark_failed(self, run: SandboxRun):
        """Mark remediation as failed."""
        try:
            run.rollback_notes = f"Failed validation at {datetime.now(timezone.utc)} - issue recurring"
            db.session.add(run)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to mark run {run.run_id} as failed: {e}")
            db.session.rollback()

    def _extract_issue_id(self, fingerprint: str) -> Optional[str]:
        """Extract Sentry issue ID from fingerprint."""
        # Fingerprint format: "SENTRY-123:..."
        if fingerprint.startswith('SENTRY-'):
            # It might be "SENTRY-123" or "SENTRY-123:module:error"
            return fingerprint.split(':')[0]
        return None
