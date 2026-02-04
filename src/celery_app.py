"""
Celery Application Configuration
Shopify Multi-Supplier Platform

This is a minimal placeholder for Phase 2 Docker setup.
Full implementation with tasks added in Phase 6.

Usage:
    # Run worker (from docker-compose)
    celery -A src.celery_app worker --loglevel=info

    # Run worker locally (for debugging)
    celery -A src.celery_app worker --loglevel=debug --concurrency=1
"""
import os
from celery import Celery

# Create Celery app
app = Celery('shopify_platform')

# Configuration from environment variables
app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),

    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,  # Fair task distribution
    task_acks_late=True,           # Retry on worker crash

    # Result expiration (1 hour)
    result_expires=3600,
)


# Example task (placeholder - real tasks in Phase 6)
@app.task(bind=True)
def debug_task(self):
    """Test task to verify Celery is working."""
    print(f'Request: {self.request!r}')
    return {'status': 'ok', 'message': 'Celery is working!'}


# Task discovery - will find tasks in src.tasks module (Phase 6)
# app.autodiscover_tasks(['src.tasks'])
