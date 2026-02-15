"""Celery task package."""

# Imported for Celery autodiscovery side-effects.
from src.tasks import audits, chat_bulk, control, ingest, resolution_apply, scrape_jobs  # noqa: F401
