"""Scraper service task entrypoints used by dedicated scraper workers."""
from __future__ import annotations

from src.celery_app import app


def _scrape_payload(payload: dict | None) -> dict:
    # Placeholder for Phase 8 resolver integration; returns deterministic ack now.
    payload = payload or {}
    return {"accepted": True, "payload_keys": sorted(payload.keys())}


@app.task(name="src.tasks.scrape_jobs.run_scraper_job_t1")
def run_scraper_job_t1(payload: dict | None = None) -> dict:
    return _scrape_payload(payload)


@app.task(name="src.tasks.scrape_jobs.run_scraper_job_t2")
def run_scraper_job_t2(payload: dict | None = None) -> dict:
    return _scrape_payload(payload)


@app.task(name="src.tasks.scrape_jobs.run_scraper_job_t3")
def run_scraper_job_t3(payload: dict | None = None) -> dict:
    return _scrape_payload(payload)

