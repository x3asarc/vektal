"""
Docker secrets utility with environment variable fallback.

In Docker Swarm/Compose with secrets, sensitive values are mounted as files
at /run/secrets/{secret_name}. This module provides a unified interface
that works both in Docker (reads files) and local development (reads env vars).

Usage:
    from src.core.secrets import get_secret

    api_key = get_secret("GEMINI_API_KEY")
    db_password = get_secret("DB_PASSWORD", default="dev-password")
"""

import os
import logging

logger = logging.getLogger(__name__)

SECRETS_DIR = "/run/secrets"


def get_secret(name: str, default: str = None) -> str | None:
    """
    Get a secret value from Docker secrets file or environment variable.

    Priority:
    1. Docker secret file at /run/secrets/{name}
    2. Environment variable {name}
    3. Default value (if provided)

    Args:
        name: Secret name (e.g., "GEMINI_API_KEY")
        default: Default value if secret not found

    Returns:
        Secret value or default
    """
    secret_path = os.path.join(SECRETS_DIR, name)

    # Try Docker secret file first
    if os.path.isfile(secret_path):
        try:
            with open(secret_path, 'r') as f:
                value = f.read().strip()
                logger.debug(f"Secret {name} loaded from Docker secrets file")
                return value
        except (IOError, PermissionError) as e:
            logger.warning(f"Could not read secret file {secret_path}: {e}")

    # Fall back to environment variable
    env_value = os.getenv(name)
    if env_value is not None:
        logger.debug(f"Secret {name} loaded from environment variable")
        return env_value

    # Return default
    if default is not None:
        logger.debug(f"Secret {name} using default value")
    return default
