"""Celery application configuration for Phase 6 job orchestration."""
from __future__ import annotations

import os
import uuid
from types import SimpleNamespace

try:
    from celery import Celery
    from kombu import Queue
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal test environments
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
    },
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


app.autodiscover_tasks(["src.tasks"])
