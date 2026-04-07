"""Task dispatch utilities that support Celery or FastAPI background execution."""
import logging
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks

from .config import settings

logger = logging.getLogger(__name__)


def dispatch_task(background_tasks: BackgroundTasks | None, task_callable: Any, *args, **kwargs) -> str:
    """Dispatch a task through Celery when enabled, otherwise run via FastAPI background tasks."""
    if settings.ENABLE_CELERY:
        try:
            task = task_callable.delay(*args, **kwargs)
            return task.id
        except Exception as exc:
            logger.warning("Celery dispatch failed, falling back to FastAPI background tasks: %s", exc)

    task_id = f"local-{uuid4().hex}"
    if background_tasks is not None:
        background_tasks.add_task(task_callable, *args, **kwargs)
    else:
        task_callable(*args, **kwargs)
    return task_id
