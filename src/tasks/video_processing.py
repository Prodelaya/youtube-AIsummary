"""
Tareas de Celery para procesamiento de videos.

Este modulo contiene las tareas asincronas relacionadas con el pipeline
de procesamiento de videos: descarga, transcripcion y resumen.

Tareas:
- process_video_task: Ejecuta el pipeline completo para un video
- retry_failed_video_task: Reintenta videos en estado 'failed'

Las tareas usan VideoProcessingService que orquesta todos los servicios.
"""

import asyncio
import logging
import time
from uuid import UUID

from celery import Task
from sqlalchemy.orm import Session

from src.core.celery_app import celery_app
from src.core.database import SessionLocal
from src.core.metrics import metrics
from src.models.video import VideoStatus
from src.repositories.video_repository import VideoRepository
from src.services.video_processing_service import (
    InvalidVideoStateError,
    VideoNotFoundError,
    VideoProcessingService,
)

# ==================== LOGGER ====================

logger = logging.getLogger(__name__)


# ==================== CUSTOM TASK BASE ====================


class DatabaseTask(Task):
    """
    Task base customizada que maneja sesiones de BD automaticamente.

    Garantiza que cada tarea:
    - Tiene una sesion de BD limpia
    - Cierra la sesion al finalizar
    - Hace rollback en caso de error
    """

    _db: Session | None = None

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Hook ejecutado despues de que la tarea retorna.

        Cierra la sesion de BD.
        """
        if self._db is not None:
            self._db.close()
            self._db = None

    @property
    def db(self) -> Session:
        """
        Lazy-load de sesion de BD.

        Returns:
            Session de SQLAlchemy.
        """
        if self._db is None:
            self._db = SessionLocal()
        return self._db


# ==================== TAREAS ====================


@celery_app.task(
    name="process_video",
    base=DatabaseTask,
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutos entre reintentos
    autoretry_for=(Exception,),  # Retry automatico para cualquier excepcion
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=3600,  # Max 1 hora entre reintentos
    retry_jitter=True,  # Jitter aleatorio para evitar thundering herd
)
def process_video_task(self, video_id_str: str) -> dict:
    """
    Tarea de Celery que ejecuta el pipeline completo de procesamiento.

    Esta tarea:
    1. Obtiene el video de la BD
    2. Valida que este en estado procesable
    3. Ejecuta VideoProcessingService.process_video()
    4. Retorna resultado o propaga error

    Args:
        video_id_str: UUID del video en formato string.

    Returns:
        dict con status y video_id si exitoso.

    Raises:
        VideoNotFoundError: Si el video no existe.
        InvalidVideoStateError: Si el video no esta en estado procesable.
        Exception: Cualquier error del pipeline (se reintenta automaticamente).

    Example:
        >>> task = process_video_task.delay("123e4567-e89b-12d3-a456-426614174000")
        >>> task.id
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        >>> task.status
        'PENDING'
    """
    video_id = UUID(video_id_str)
    start_time = time.time()

    logger.info(
        "process_video_task_started",
        extra={
            "video_id": video_id_str,
            "task_id": self.request.id,
            "retries": self.request.retries,
        },
    )

    try:
        # Validar que el video existe
        video_repo = VideoRepository(self.db)
        video = video_repo.get_by_id(video_id)

        if not video:
            logger.error(
                "process_video_task_video_not_found",
                extra={"video_id": video_id_str, "task_id": self.request.id},
            )
            raise VideoNotFoundError(f"Video {video_id} not found")

        # Validar estado
        if video.status not in {VideoStatus.PENDING, VideoStatus.FAILED}:
            logger.warning(
                "process_video_task_invalid_state",
                extra={
                    "video_id": video_id_str,
                    "task_id": self.request.id,
                    "current_status": video.status.value,
                },
            )
            raise InvalidVideoStateError(
                f"Video {video_id} is in state '{video.status.value}', "
                "only 'pending' or 'failed' videos can be processed"
            )

        # Ejecutar pipeline (async desde sync Celery task)
        service = VideoProcessingService()
        processed_video = asyncio.run(service.process_video(self.db, video_id))

        # Métricas de éxito
        duration = time.time() - start_time
        metrics.celery_task_duration_seconds.labels(task_name="process_video").observe(duration)
        metrics.celery_task_total.labels(task_name="process_video", status="success").inc()

        logger.info(
            "process_video_task_completed",
            extra={
                "video_id": video_id_str,
                "task_id": self.request.id,
                "final_status": processed_video.status.value,
                "retries": self.request.retries,
                "duration_seconds": round(duration, 2),
            },
        )

        return {
            "status": "completed",
            "video_id": video_id_str,
            "final_status": processed_video.status.value,
        }

    except (VideoNotFoundError, InvalidVideoStateError):
        # No reintentar estos errores (son permanentes)
        duration = time.time() - start_time
        metrics.celery_task_duration_seconds.labels(task_name="process_video").observe(duration)
        metrics.celery_task_total.labels(task_name="process_video", status="failed").inc()

        logger.error(
            "process_video_task_permanent_error",
            extra={
                "video_id": video_id_str,
                "task_id": self.request.id,
            },
        )
        raise

    except Exception as exc:
        # Log del error y permitir retry automatico
        duration = time.time() - start_time
        metrics.celery_task_duration_seconds.labels(task_name="process_video").observe(duration)

        # Solo incrementar retry counter si hay retry
        if self.request.retries > 0:
            metrics.celery_task_retries_total.labels(task_name="process_video").inc()

        metrics.celery_task_total.labels(task_name="process_video", status="retry").inc()

        logger.error(
            "process_video_task_error",
            extra={
                "video_id": video_id_str,
                "task_id": self.request.id,
                "error": str(exc),
                "error_type": type(exc).__name__,
                "retries": self.request.retries,
            },
            exc_info=True,
        )
        # Celery hara retry automaticamente
        raise


@celery_app.task(
    name="retry_failed_video",
    base=DatabaseTask,
    bind=True,
    max_retries=1,  # Solo 1 reintento para retry manual
)
def retry_failed_video_task(self, video_id_str: str) -> dict:
    """
    Tarea para reintentar el procesamiento de videos en estado 'failed'.

    Similar a process_video_task pero solo acepta videos en estado FAILED.
    Usado cuando el usuario manualmente solicita retry via API.

    Args:
        video_id_str: UUID del video en formato string.

    Returns:
        dict con status y video_id.

    Raises:
        VideoNotFoundError: Si el video no existe.
        InvalidVideoStateError: Si el video no esta en estado 'failed'.

    Example:
        >>> task = retry_failed_video_task.delay("123e4567-e89b-12d3-a456-426614174000")
    """
    video_id = UUID(video_id_str)

    logger.info(
        "retry_failed_video_task_started",
        extra={"video_id": video_id_str, "task_id": self.request.id},
    )

    try:
        # Validar que el video existe y esta failed
        video_repo = VideoRepository(self.db)
        video = video_repo.get_by_id(video_id)

        if not video:
            raise VideoNotFoundError(f"Video {video_id} not found")

        if video.status != VideoStatus.FAILED:
            raise InvalidVideoStateError(
                f"Video {video_id} is in state '{video.status.value}', "
                "only 'failed' videos can be retried via this endpoint"
            )

        # Reiniciar estado a PENDING
        video.status = VideoStatus.PENDING
        self.db.commit()

        # Ejecutar pipeline
        service = VideoProcessingService()
        processed_video = asyncio.run(service.process_video(self.db, video_id))

        logger.info(
            "retry_failed_video_task_completed",
            extra={
                "video_id": video_id_str,
                "task_id": self.request.id,
                "final_status": processed_video.status.value,
            },
        )

        return {
            "status": "completed",
            "video_id": video_id_str,
            "final_status": processed_video.status.value,
        }

    except Exception as exc:
        logger.error(
            "retry_failed_video_task_error",
            extra={
                "video_id": video_id_str,
                "task_id": self.request.id,
                "error": str(exc),
            },
            exc_info=True,
        )
        raise
