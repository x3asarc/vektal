"""Docker compose routing tests for worker/scraper/flower services."""
from pathlib import Path

import yaml


def _compose():
    path = Path("docker-compose.yml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_compose_has_worker_scraper_and_flower_services():
    services = _compose()["services"]
    assert "celery_worker" in services
    assert "celery_scraper" in services
    assert "flower" in services


def test_compose_commands_have_explicit_queue_split():
    services = _compose()["services"]
    worker_cmd = services["celery_worker"]["command"]
    scraper_cmd = services["celery_scraper"]["command"]
    assert "control,interactive.t1,interactive.t2,interactive.t3" in worker_cmd
    assert "batch.t1,batch.t2,batch.t3" in scraper_cmd


def test_compose_uses_centralized_logging_policy():
    services = _compose()["services"]
    for service_name in ("backend", "celery_worker", "celery_scraper", "flower"):
        logging_config = services[service_name]["logging"]
        assert logging_config["driver"] == "json-file"
        assert logging_config["options"]["max-size"] == "10m"
        assert logging_config["options"]["max-file"] == "5"

