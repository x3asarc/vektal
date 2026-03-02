from typing import Dict, Optional, Tuple, Any
from src.models.remedy_templates import RemedyTemplate
from src.assistant.session_primer import SessionPrimer
from src.core.memory_loader import MemoryLoader
from src.core.llm_client import get_llm_client
import logging
import json

logger = logging.getLogger(__name__)

class FixGenerator:
    """Generates fixes using template-first strategy with LLM fallback."""

    def __init__(self):
        self.session_primer = SessionPrimer(MemoryLoader())
        self.llm_client = get_llm_client()

    def generate_fix(
        self,
        error_type: str,
        error_message: str,
        affected_module: str,
        traceback: str,
        classification_evidence: Dict
    ) -> Tuple[Dict, float]:
        """Generate fix using template or LLM.

        Returns: (fix_payload, confidence)
        """
        # Step 1: Template matching (deterministic, fast)
        template_fix = self._try_template_match(error_type, affected_module)
        if template_fix:
            return template_fix, 0.95  # High confidence for template

        # Step 2: LLM generation (novel failures)
        return self._generate_with_llm(
            error_type, error_message, affected_module, traceback, classification_evidence
        )

    def _try_template_match(
        self, error_type: str, affected_module: str
    ) -> Optional[Dict]:
        """Query template cache for matching remedies."""
        fingerprint = f"{affected_module}:{error_type}"
        # RemedyTemplate.query_relevant is expected to be a class method returning list of templates
        try:
            templates = RemedyTemplate.query_relevant(fingerprint, limit=1)
        except Exception as e:
            logger.debug(f"Template query failed (expected if DB not initialized): {e}")
            return None

        if templates and templates[0].confidence >= 0.9:
            template = templates[0]
            logger.info(f"Template match found: {template.fingerprint}")
            return {
                'type': 'template',
                'template_id': template.template_id,
                'changed_files': self._parse_remedy_payload(template.remedy_payload),
                'description': template.description
            }

        return None

    def _generate_with_llm(
        self,
        error_type: str,
        error_message: str,
        affected_module: str,
        traceback: str,
        classification_evidence: Dict
    ) -> Tuple[Dict, float]:
        """Generate fix using LLM with session context."""
        # Load session context
        try:
            session_context = self.session_primer.load_session_context(
                failure_context=f"{error_type} in {affected_module}"
            )
        except Exception as e:
            logger.warning(f"Session context loading failed: {e}")
            session_context = "Session context unavailable."

        # Construct prompt
        prompt = f'''Generate a Python fix for this error.

Session Context:
{session_context}

Error Details:
Type: {error_type}
Message: {error_message}
Module: {affected_module}
Traceback (last 10 lines):
{self._truncate_traceback(traceback, 10)}

Classification Evidence:
{classification_evidence}

Respond in JSON format:
{{
    "changed_files": {{
        "path/to/file.py": "complete fixed file content"
    }},
    "description": "Brief description of fix",
    "confidence": 0.0-1.0
}}
'''

        # Adaptive model selection (15-RESEARCH.md Section 3.A)
        model = self._select_model(affected_module, len(traceback))

        try:
            response = self.llm_client.complete(
                prompt=prompt,
                model=model,
                temperature=0.2,  # Low temp for deterministic fixes
                max_tokens=4000
            )

            # Clean markdown if LLM includes it
            text = response.strip()
            if text.startswith("```"):
                import re
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)

            fix_data = json.loads(text)

            return {
                'type': 'llm_generated',
                'changed_files': fix_data.get('changed_files', {}),
                'description': fix_data.get('description', 'No description provided'),
                'llm_model': model
            }, float(fix_data.get('confidence', 0.7))

        except Exception as e:
            logger.error(f"LLM fix generation failed: {e}")
            return {
                'type': 'failed',
                'error': str(e)
            }, 0.0

    def _select_model(self, affected_module: str, traceback_len: int) -> str:
        """Adaptive model selection based on complexity."""
        # Simple config changes -> Flash
        if 'config' in affected_module or traceback_len < 500:
            return 'google/gemini-2.0-flash-001'

        # Multi-file changes -> Sonnet
        if traceback_len > 1000:
            return 'anthropic/claude-3.5-sonnet'

        # Default: Flash
        return 'google/gemini-2.0-flash-001'

    def _parse_remedy_payload(self, payload: str) -> Dict:
        """Parse serialized remedy payload."""
        if isinstance(payload, dict):
            return payload
        try:
            return json.loads(payload)
        except Exception:
            return {}

    def _truncate_traceback(self, traceback: str, last_n_lines: int) -> str:
        if not traceback:
            return ""
        lines = traceback.strip().split('\n')
        return '\n'.join(lines[-last_n_lines:])
