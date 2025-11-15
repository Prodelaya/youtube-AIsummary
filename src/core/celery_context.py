"""
Context manager para Celery tasks con Request ID y logging estructurado.

Este módulo proporciona utilities para enriquecer el contexto de logging
en Celery workers, permitiendo correlación de logs entre API y workers.

Example:
    >>> from src.core.celery_context import task_context
    >>> @celery_app.task
    >>> def process_video_task(video_id: str):
    >>>     with task_context(task_name="process_video", video_id=video_id):
    >>>         # Todos los logs aquí tendrán request_id y video_id
    >>>         logger.info("processing_started")
"""

import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog

from src.core.logging_config import get_logger

logger = get_logger(__name__)


@contextmanager
def task_context(**context_vars: Any) -> Generator[None, None, None]:
    """
    Context manager para inyectar contexto en logs de Celery tasks.

    Genera un Request ID único para la task y lo inyecta en el contexto
    de structlog junto con cualquier variable adicional proporcionada.

    Args:
        **context_vars: Variables de contexto a inyectar (task_name, video_id, etc.).

    Yields:
        None

    Example:
        >>> with task_context(task_name="process_video", video_id=str(video_id)):
        >>>     logger.info("video_processing_started")
        >>>     # Log incluirá: request_id, task_name, video_id
    """
    # Generar Request ID único para esta task
    request_id = str(uuid.uuid4())

    # Preparar contexto completo
    full_context = {"request_id": request_id, **context_vars}

    # Inyectar en structlog
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**full_context)

    # Logging de inicio de task
    start_time = time.time()

    logger.info(
        "task_started",
        **context_vars,
    )

    try:
        yield

        # Logging de finalización exitosa
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "task_completed",
            duration_ms=duration_ms,
            **context_vars,
        )

    except Exception as exc:
        # Logging de error
        duration_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "task_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=duration_ms,
            exc_info=True,
            **context_vars,
        )

        raise

    finally:
        # Limpiar contexto
        structlog.contextvars.clear_contextvars()


def bind_task_context(**context_vars: Any) -> None:
    """
    Bind adicional de variables al contexto actual.

    Útil para añadir contexto progresivamente durante la ejecución de una task.

    Args:
        **context_vars: Variables de contexto a añadir.

    Example:
        >>> with task_context(task_name="process_video"):
        >>>     video = get_video()
        >>>     bind_task_context(video_id=str(video.id), youtube_id=video.youtube_id)
        >>>     # Los siguientes logs incluirán video_id y youtube_id
        >>>     logger.info("video_downloaded")
    """
    structlog.contextvars.bind_contextvars(**context_vars)
