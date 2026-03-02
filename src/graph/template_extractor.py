import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.graphiti_client import get_graphiti_client
from src.models import db
from src.models.remedy_templates import RemedyTemplate

logger = logging.getLogger(__name__)


class TemplateExtractor:
    """
    Extract successful fixes into reusable templates.

    Learning-loop responsibilities:
    1. Promote successful fixes (>=2 applications) into Neo4j + PostgreSQL cache.
    2. Create template similarity relationships in Neo4j.
    3. Keep PostgreSQL cache synchronized from graph memory.
    4. Expire templates when affected files materially diverge.
    """

    def __init__(self, graph_client: Any = None):
        self.graph_client = graph_client if graph_client is not None else get_graphiti_client()

    def _safe_graph_query(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = self.graph_client
        if client is None:
            return []
        try:
            if hasattr(client, "execute_query"):
                rows = client.execute_query(query, params)
                return [dict(row) for row in rows] if rows else []

            driver = getattr(client, "driver", None)
            if driver is None:
                return []
            with driver.session() as session:
                result = session.run(query, params)
                return [dict(row) for row in result]
        except Exception as exc:
            logger.debug("Graph query failed in TemplateExtractor: %s", exc)
            return []

    def check_promotion_eligibility(self, fingerprint: str) -> bool:
        """
        Promotion threshold: >=2 successful applications.
        """
        if not self.graph_client:
            logger.debug("Graph unavailable, skipping promotion check.")
            return False

        query = """
        MATCH (r:SandboxRun {verdict: 'GREEN', fingerprint: $fingerprint})
        RETURN count(r) AS success_count
        """
        result = self._safe_graph_query(query, {"fingerprint": fingerprint})
        success_count = int(result[0].get("success_count", 0)) if result else 0
        logger.info("Promotion check for %s: %s successes", fingerprint, success_count)
        return success_count >= 2

    def extract_and_promote(
        self,
        fix_payload: Dict[str, Any],
        confidence: float,
        fingerprint: str,
    ) -> Optional[str]:
        """
        Promote fix to Neo4j template node and PostgreSQL cache.
        """
        template_id = str(uuid.uuid4())
        changed_files = self._normalize_changed_files(fix_payload.get("changed_files"))
        payload_json = json.dumps(changed_files)
        description = str(fix_payload.get("description", ""))

        if self.graph_client:
            template_query = """
            CREATE (t:RemedyTemplate {
                template_id: $template_id,
                fingerprint: $fingerprint,
                description: $description,
                remedy_payload: $payload,
                confidence: $confidence,
                application_count: 2,
                success_count: 2,
                affected_files: $affected_files,
                last_applied_at: datetime(),
                created_at: datetime()
            })
            RETURN t.template_id AS template_id
            """
            created = self._safe_graph_query(
                template_query,
                {
                    "template_id": template_id,
                    "fingerprint": fingerprint,
                    "description": description,
                    "payload": payload_json,
                    "confidence": float(confidence),
                    "affected_files": changed_files,
                },
            )
            if not created:
                logger.warning("Neo4j template creation returned no rows for %s", fingerprint)

            self._create_similarity_relationships(
                template_id=template_id,
                fingerprint=fingerprint,
            )
            logger.info("Promoted %s to Neo4j template %s", fingerprint, template_id)

        record = {
            "template_id": template_id,
            "fingerprint": fingerprint,
            "description": description,
            "remedy_payload": payload_json,
            "confidence": float(confidence),
            "application_count": 2,
            "success_count": 2,
            "affected_files_json": changed_files,
            "last_applied_at": datetime.now(timezone.utc),
        }
        try:
            RemedyTemplate.upsert_from_graph(record)
            logger.info("Promoted %s to PostgreSQL cache.", fingerprint)
            return template_id
        except Exception as exc:
            logger.error("Failed to sync template to PostgreSQL: %s", exc)
            db.session.rollback()
            return None

    def _create_similarity_relationships(self, template_id: str, fingerprint: str) -> int:
        """
        Link template to similar templates by fingerprint/module/error-type affinity.
        """
        if not self.graph_client:
            return 0

        module_prefix, error_type = self._split_fingerprint(fingerprint)
        query = """
        MATCH (t:RemedyTemplate {template_id: $template_id})
        MATCH (other:RemedyTemplate)
        WHERE other.template_id <> $template_id
          AND (
              other.fingerprint = $fingerprint
              OR ($module_prefix <> '' AND other.fingerprint STARTS WITH $module_prefix)
              OR ($error_type <> '' AND other.fingerprint ENDS WITH (':' + $error_type))
          )
        MERGE (t)-[rel:SIMILAR_TO]->(other)
        ON CREATE SET rel.created_at = datetime(), rel.strategy = 'fingerprint-affinity'
        RETURN count(rel) AS linked_count
        """
        rows = self._safe_graph_query(
            query,
            {
                "template_id": template_id,
                "fingerprint": fingerprint,
                "module_prefix": module_prefix,
                "error_type": error_type,
            },
        )
        return int(rows[0].get("linked_count", 0)) if rows else 0

    def sync_templates_to_cache(self, min_application_count: int = 3, recent_days: int = 7) -> int:
        """
        Sync recent/high-signal templates from Neo4j into PostgreSQL cache.
        """
        if not self.graph_client:
            return 0

        query = """
        MATCH (t:RemedyTemplate)
        WHERE coalesce(t.application_count, 0) >= $min_application_count
           OR t.last_applied_at > datetime() - duration({days: $recent_days})
           OR t.created_at > datetime() - duration({days: $recent_days})
        RETURN properties(t) AS template
        """
        rows = self._safe_graph_query(
            query,
            {"min_application_count": int(min_application_count), "recent_days": int(recent_days)},
        )
        synced = 0
        for row in rows:
            template = row.get("template") or row.get("t") or row
            if not isinstance(template, dict):
                continue
            try:
                RemedyTemplate.upsert_from_graph(template)
                synced += 1
            except Exception as exc:
                logger.warning("Template cache upsert failed: %s", exc)
                db.session.rollback()
        return synced

    def expire_templates_for_changed_files(
        self,
        changed_files: List[str],
        overlap_threshold: float = 0.5,
    ) -> int:
        """
        Expire templates with significant overlap against changed files.
        """
        normalized = [str(path) for path in changed_files if path]
        if not normalized:
            return 0

        now = datetime.now(timezone.utc)
        try:
            candidates = (
                db.session.query(RemedyTemplate)
                .filter(db.or_(RemedyTemplate.expires_at.is_(None), RemedyTemplate.expires_at > now))
                .all()
            )
        except Exception as exc:
            logger.warning("Template expiry query skipped due DB error: %s", exc)
            db.session.rollback()
            return 0

        expired = 0
        for template in candidates:
            if template.expire_if_files_changed(normalized, overlap_threshold=overlap_threshold):
                expired += 1
        return expired

    @staticmethod
    def _normalize_changed_files(changed_files: Any) -> List[str]:
        if isinstance(changed_files, dict):
            return [str(path) for path in changed_files.keys() if path]
        if isinstance(changed_files, list):
            return [str(path) for path in changed_files if path]
        return []

    @staticmethod
    def _split_fingerprint(fingerprint: str) -> tuple[str, str]:
        if ":" not in fingerprint:
            return "", ""
        module_prefix, error_type = fingerprint.rsplit(":", 1)
        return module_prefix.strip(), error_type.strip()
