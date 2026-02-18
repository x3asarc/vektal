"""Centralized logging defaults for Docker services."""

LOG_FORMAT = (
    "%(asctime)s %(levelname)s [%(name)s] "
    "[job_id=%(job_id)s store_id=%(store_id)s] %(message)s"
)

DEFAULT_DOCKER_LOGGING = {
    "driver": "json-file",
    "options": {
        "max-size": "10m",
        "max-file": "5",
        "mode": "non-blocking",
    },
}


def get_docker_logging_config() -> dict:
    """Expose compose-friendly logging defaults."""
    return DEFAULT_DOCKER_LOGGING.copy()

