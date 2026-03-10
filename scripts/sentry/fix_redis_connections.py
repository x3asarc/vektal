"""Fix Redis connection pooling issues in Celery configuration."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

def analyze_redis_config():
    """Analyze current Redis configuration."""
    from src.config import settings

    print("Current Redis configuration:")
    print(f"  REDIS_URL: {settings.REDIS_URL}")
    print(f"  CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")
    print(f"  CELERY_RESULT_BACKEND: {settings.CELERY_RESULT_BACKEND}")

    # Check for Redis connection pool settings
    celery_config = Path(PROJECT_ROOT) / "src" / "celery_app.py"
    if celery_config.exists():
        with open(celery_config, "r", encoding="utf-8") as f:
            content = f.read()

        print("\nCelery configuration file:")
        if "broker_transport_options" in content:
            print("  ✓ broker_transport_options found")
        else:
            print("  ✗ broker_transport_options NOT configured")

        if "redis_socket_connect_timeout" in content:
            print("  ✓ socket timeout configured")
        else:
            print("  ✗ socket timeout NOT configured")

    print("\nRecommended fixes:")
    print("1. Add broker_transport_options with visibility_timeout")
    print("2. Add redis connection pool settings")
    print("3. Add socket_connect_timeout and socket_keepalive")
    print("4. Increase retry backoff for connection failures")

if __name__ == "__main__":
    analyze_redis_config()
