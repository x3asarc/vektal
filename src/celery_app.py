"""Celery application configuration for Phase 6 job orchestration."""
from __future__ import annotations

import os
import socket
import uuid
from types import SimpleNamespace

try:
    from celery import Celery
    from celery.signals import task_failure, task_success, worker_ready, worker_shutdown
    from kombu import Queue
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal test environments
    task_failure = None
    task_success = None
    worker_ready = None
    worker_shutdown = None

    class Queue:  # type: ignore[override]
        def __init__(self, name: str):
            self.name = name

    class _Conf(dict):
        def __getattr__(self, item):
            return self.get(item)

        def __setattr__(self, key, value):
            self[key] = value

        def update(self, *args, **kwargs):
            super().update(*args, **kwargs)

    class _FakeInspect:
        def active_queues(self):
            return {}

    class _FakeControl:
        def inspect(self):
            return _FakeInspect()

        def revoke(self, *_args, **_kwargs):
            return None

    class _FakeTask:
        def __init__(self, func, bind: bool = False, name: str | None = None):
            self.run = func
            self.bind = bind
            self.name = name or func.__name__
            self.request = SimpleNamespace(id=f"fake-{uuid.uuid4().hex}")

        def __call__(self, *args, **kwargs):
            if self.bind:
                return self.run(self, *args, **kwargs)
            return self.run(*args, **kwargs)

    class _FakeAsyncResult:
        def __init__(self):
            self.id = f"fake-{uuid.uuid4().hex}"

    class Celery:  # type: ignore[override]
        def __init__(self, _name: str):
            self.conf = _Conf()
            self.control = _FakeControl()
            self._tasks = {}

        def task(self, *dargs, **dkwargs):
            bind = dkwargs.get("bind", False)
            task_name = dkwargs.get("name")

            def decorator(func):
                task = _FakeTask(func, bind=bind, name=task_name)
                self._tasks[task.name] = task
                return task

            if dargs and callable(dargs[0]):
                return decorator(dargs[0])
            return decorator

        def send_task(self, _name: str, kwargs=None, queue=None):
            return _FakeAsyncResult()

        def autodiscover_tasks(self, _packages):
            return None

from src.jobs.queueing import ALL_QUEUES, TASK_ROUTES
from src.config.sentry_config import configure_sentry
from src.core.sentry_metrics import count as sentry_count
from src.core.graphiti_client import validate_graph_config

# Worker process should report to the workers Sentry project DSN.
configure_sentry(runtime="workers")

app = Celery("shopify_platform")

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)

app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    task_default_queue="control",
    task_queues=tuple(Queue(name) for name in ALL_QUEUES),
    task_routes=TASK_ROUTES,
    task_annotations={
        "src.tasks.chat_bulk.run_chat_bulk_action": {
            "acks_late": True,
        },
    },
    beat_schedule={
        "dispatch-pending-audits": {
            "task": "src.tasks.audits.dispatch_pending_audits",
            "schedule": float(os.getenv("AUDIT_DISPATCH_INTERVAL_SECONDS", "10")),
        },
        "cleanup-old-jobs": {
            "task": "src.tasks.control.cleanup_old_jobs",
            "schedule": float(os.getenv("JOB_RETENTION_SWEEP_SECONDS", "3600")),
            "args": (
                int(os.getenv("JOB_RETENTION_DAYS", "30")),
                True,
            ),
        },
        "redis-health-check": {
            "task": "src.celery_app.redis_health_check",
            "schedule": 30.0,  # Every 30s
        },
    },
    # Redis connection resilience (prevents connection retry exhaustion)
    # Issue 101522185: Connection to Redis lost (713 events)
    # Issue 101522288: Retry limit exceeded (35 events)
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,  # Infinite retries with exponential backoff
    broker_connection_retry=True,
    # Exponential backoff tuning: extends retry window from 60s to ~300s (5 minutes)
    broker_connection_interval_start=2,  # Start with 2s
    broker_connection_interval_step=2,  # Add 2s each retry
    broker_connection_interval_max=30,  # Cap at 30s per retry
    broker_transport_options={
        "socket_connect_timeout": 5,  # Fail fast to trigger retry logic
        "socket_keepalive": True,  # Enable TCP keepalive
        "socket_keepalive_options": {
            socket.TCP_KEEPIDLE: int(os.getenv("REDIS_KEEPALIVE_IDLE", "60")),  # Cloud LB-safe default
            socket.TCP_KEEPINTVL: int(os.getenv("REDIS_KEEPALIVE_INTERVAL", "10")),
            socket.TCP_KEEPCNT: int(os.getenv("REDIS_KEEPALIVE_COUNT", "3")),
        },
        "retry_on_timeout": True,
        "max_connections": 50,
        "visibility_timeout": 3600,  # 1 hour task visibility
        "health_check_interval": 10,  # Check connection health every 10s
    },
    # Apply same resilience to result backend (issue 101522185 + 101522288)
    result_backend_transport_options={
        "socket_connect_timeout": 5,  # Fail fast to trigger retry logic
        "socket_keepalive": True,  # Enable TCP keepalive
        "socket_keepalive_options": {
            socket.TCP_KEEPIDLE: int(os.getenv("REDIS_KEEPALIVE_IDLE", "60")),  # Cloud LB-safe default
            socket.TCP_KEEPINTVL: int(os.getenv("REDIS_KEEPALIVE_INTERVAL", "10")),
            socket.TCP_KEEPCNT: int(os.getenv("REDIS_KEEPALIVE_COUNT", "3")),
        },
        "retry_on_timeout": True,
        "max_connections": 50,
        "health_check_interval": 10,
    },
    redis_backend_health_check_interval=10,  # More frequent health checks
    redis_retry_on_timeout=True,
    redis_socket_connect_timeout=5,
    redis_socket_keepalive=True,
)


_flask_app = None


def _get_flask_app():
    """Lazily create Flask app for Celery worker process context."""
    global _flask_app
    if _flask_app is None:
        from src.api.app import create_openapi_app

        _flask_app = create_openapi_app()
    return _flask_app


if hasattr(app, "Task"):
    _BaseTask = app.Task

    class FlaskAppContextTask(_BaseTask):  # pragma: no cover - exercised in runtime/UAT
        abstract = True

        def __call__(self, *args, **kwargs):
            flask_app = _get_flask_app()
            with flask_app.app_context():
                return _BaseTask.__call__(self, *args, **kwargs)

    app.Task = FlaskAppContextTask


@app.task(bind=True)
def debug_task(self):
    """Health task used by tests and smoke checks."""
    return {"task_id": self.request.id, "status": "ok"}


@app.task(bind=True)
def redis_health_check(self):
    """Periodic health check - exit worker if Redis is dead."""
    import sys
    try:
        app.connection().ensure_connection(max_retries=1, timeout=5)
    except Exception as exc:
        print(f"FATAL: Redis health check failed: {exc}", file=sys.stderr)
        sys.exit(1)  # Exit for Docker restart


# Validate graph credentials at worker startup.
# CRITICAL-logs if GRAPH_ORACLE_ENABLED=true but NEO4J_PASSWORD/URI missing.
# Blast radius: emit_episode, consistency_daemon, incremental_sync, query_templates,
# search_expand_bridge, similarity_detector all silently return empty/None without these.
validate_graph_config()

app.autodiscover_tasks(["src.tasks"])


if task_success is not None:
    @task_success.connect
    def _on_task_success(sender=None, result=None, **_kwargs):
        task_name = getattr(sender, "name", "unknown")
        sentry_count("workers.task.success", 1, tags={"task": task_name})


if task_failure is not None:
    @task_failure.connect
    def _on_task_failure(sender=None, exception=None, **_kwargs):
        task_name = getattr(sender, "name", "unknown")
        error_type = type(exception).__name__ if exception is not None else "unknown"
        sentry_count(
            "workers.task.failure",
            1,
            tags={"task": task_name, "error_type": error_type},
        )


if worker_shutdown is not None:
    @worker_shutdown.connect
    def _cleanup_connections(**_kwargs):
        """Gracefully close Redis connections on worker shutdown."""
        try:
            app.connection_pool.force_close_all()
        except Exception:
            pass  # Best-effort cleanup


# Critical: Exit worker process if Redis connection fails during startup or runtime.
# Without this, workers enter zombie state when Redis is unavailable - they log errors
# but don't exit, so Docker never restarts them. This causes 240+ retry attempts with
# no recovery until manual intervention.
if worker_ready is not None:
    @worker_ready.connect
    def _check_redis_on_startup(**_kwargs):
        """Verify Redis connection on worker startup - exit if unavailable."""
        import sys
        try:
            # Test broker connection
            app.connection().ensure_connection(max_retries=3, interval_start=1, interval_step=1)
        except Exception as exc:
            print(f"FATAL: Cannot connect to Redis broker on startup: {exc}", file=sys.stderr)
            sys.exit(1)
