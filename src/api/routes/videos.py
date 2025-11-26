"""
Router de Videos - Endpoints para gestion de videos.

Este modulo define 8 endpoints para el CRUD completo de videos:
1. POST   /videos              - Crear video manualmente
2. GET    /videos              - Listar videos (paginado, cursor-based)
3. GET    /videos/{id}         - Obtener detalle de video
4. PATCH  /videos/{id}         - Actualizar video
5. DELETE /videos/{id}         - Soft delete de video
6. POST   /videos/{id}/process - Encolar video para procesamiento
7. POST   /videos/{id}/retry   - Reintentar video fallido
8. GET    /videos/{id}/stats   - Estadisticas de un video

Todos los endpoints usan dependency injection para repos y servicios.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.auth.dependencies import get_current_user, require_admin
from src.api.dependencies import DBSession, SummaryRepo, TranscriptionRepo, VideoRepo
from src.api.schemas.common import CursorInfo, MessageResponse
from src.api.schemas.summaries import SummaryResponse
from src.api.schemas.transcriptions import TranscriptionResponse
from src.api.schemas.videos import (
    ProcessVideoResponse,
    VideoCreateRequest,
    VideoDetailResponse,
    VideoListResponse,
    VideoResponse,
    VideoStatsResponse,
)
from src.models.user import User
from src.models.video import VideoStatus
from src.services.video_processing_service import (
    InvalidVideoStateError,
    VideoNotFoundError,
)
from src.tasks.video_processing import process_video_task, retry_failed_video_task

# ==================== ROUTER ====================

router = APIRouter(prefix="/videos", tags=["Videos"])

# Limiter para rate limiting
limiter = Limiter(key_func=get_remote_address)


# ==================== ENDPOINTS ====================


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=VideoResponse,
    summary="Create video manually",
    description="Create a new video entry manually without automatic discovery.",
    responses={
        201: {
            "description": "Video created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "source_id": "987fcdeb-51a2-43f7-9876-543210987654",
                        "youtube_id": "dQw4w9WgXcQ",
                        "title": "Never Gonna Give You Up",
                        "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                        "duration_seconds": 212,
                        "status": "pending",
                        "published_at": None,
                        "metadata": {"view_count": 1000000},
                        "created_at": "2025-01-15T10:30:00Z",
                        "updated_at": "2025-01-15T10:30:00Z",
                        "deleted_at": None,
                    }
                }
            },
        },
        400: {
            "description": "Video with youtube_id already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Video with youtube_id 'dQw4w9WgXcQ' already exists",
                        "error_code": "BAD_REQUEST",
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "youtube_id"],
                                "msg": "field required",
                                "type": "value_error.missing",
                            }
                        ]
                    }
                }
            },
        },
    },
)
@limiter.limit("10/minute")  # Límite para creación de videos
def create_video(
    request: Request,
    video_data: VideoCreateRequest,
    video_repo: VideoRepo,
) -> VideoResponse:
    """
    Crear un video manualmente.

    Args:
        video_data: Datos del video a crear.
        video_repo: Repositorio de videos (inyectado).

    Returns:
        VideoResponse: Video creado.

    Raises:
        HTTPException 400: Si el youtube_id ya existe.
        HTTPException 404: Si la source_id no existe.

    Example:
        POST /api/v1/videos
        {
            "source_id": "123e4567-e89b-12d3-a456-426614174000",
            "youtube_id": "dQw4w9WgXcQ",
            "title": "Never Gonna Give You Up",
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "duration_seconds": 212
        }
    """
    # Verificar que no exista video con ese youtube_id
    existing = video_repo.get_by_youtube_id(video_data.youtube_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video with youtube_id '{video_data.youtube_id}' already exists",
        )

    # Crear video
    video = video_repo.create_video(
        source_id=video_data.source_id,
        youtube_id=video_data.youtube_id,
        title=video_data.title,
        url=str(video_data.url),
        duration_seconds=video_data.duration_seconds,
        metadata=video_data.metadata or {},
        status=VideoStatus.PENDING,
    )

    return VideoResponse.model_validate(video)


@router.get(
    "",
    response_model=VideoListResponse,
    summary="List videos",
    description="List videos with cursor-based pagination and optional filters.",
    responses={
        200: {
            "description": "List of videos with pagination info",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "source_id": "987fcdeb-51a2-43f7-9876-543210987654",
                                "youtube_id": "dQw4w9WgXcQ",
                                "title": "Never Gonna Give You Up",
                                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                                "duration_seconds": 212,
                                "status": "completed",
                                "published_at": "2009-10-25T06:57:33Z",
                                "metadata": {"view_count": 1000000},
                                "created_at": "2025-01-15T10:30:00Z",
                                "updated_at": "2025-01-15T11:45:00Z",
                                "deleted_at": None,
                            }
                        ],
                        "cursor": {
                            "has_next": True,
                            "next_cursor": "123e4567-e89b-12d3-a456-426614174000",
                            "count": 1,
                        },
                    }
                }
            },
        }
    },
)
def list_videos(
    video_repo: VideoRepo,
    limit: int = Query(20, ge=1, le=100, description="Number of videos to return"),
    cursor: UUID | None = Query(None, description="Cursor for pagination (last video ID)"),
    status_filter: VideoStatus | None = Query(
        None, alias="status", description="Filter by video status"
    ),
    source_id: UUID | None = Query(None, description="Filter by source ID"),
    include_deleted: bool = Query(False, description="Include soft-deleted videos"),
) -> VideoListResponse:
    """
    Listar videos con paginacion cursor-based.

    Args:
        video_repo: Repositorio de videos (inyectado).
        limit: Numero de videos a retornar (1-100, default 20).
        cursor: UUID del ultimo video (para paginacion).
        status_filter: Filtrar por estado (opcional).
        source_id: Filtrar por fuente (opcional).
        include_deleted: Incluir videos soft-deleted (default False).

    Returns:
        VideoListResponse: Lista paginada de videos.

    Example:
        GET /api/v1/videos?limit=20&status=completed
        GET /api/v1/videos?cursor=123e4567-e89b-12d3-a456-426614174000&limit=20
    """
    videos = video_repo.list_paginated(
        limit=limit,
        cursor=cursor,
        status=status_filter,
        source_id=source_id,
        include_deleted=include_deleted,
    )

    # Determinar si hay mas elementos
    has_next = len(videos) == limit
    next_cursor = videos[-1].id if has_next and videos else None

    # Convertir a schemas
    video_responses = [VideoResponse.model_validate(v) for v in videos]

    return VideoListResponse(
        data=video_responses,
        cursor=CursorInfo(
            has_next=has_next,
            next_cursor=next_cursor,
            count=len(video_responses),
        ),
    )


@router.get(
    "/{video_id}",
    response_model=VideoDetailResponse,
    summary="Get video details",
    description="Get detailed information about a video including transcription and summary.",
    responses={
        200: {
            "description": "Video details with transcription and summary",
        },
        404: {
            "description": "Video not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Video 123e4567-e89b-12d3-a456-426614174000 not found",
                        "error_code": "VIDEO_NOT_FOUND",
                    }
                }
            },
        },
    },
)
def get_video(
    video_id: UUID,
    video_repo: VideoRepo,
) -> VideoDetailResponse:
    """
    Obtener detalle completo de un video.

    Args:
        video_id: UUID del video.
        video_repo: Repositorio de videos (inyectado).

    Returns:
        VideoDetailResponse: Video con transcripcion y resumen.

    Raises:
        VideoNotFoundError: Si el video no existe (manejado por exception handler).

    Example:
        GET /api/v1/videos/123e4567-e89b-12d3-a456-426614174000
    """
    video = video_repo.get_by_id(video_id)
    if not video:
        raise VideoNotFoundError(f"Video {video_id} not found")

    # Construir response con relaciones
    response_data = {
        **VideoResponse.model_validate(video).model_dump(),
        "transcription": video.transcription if hasattr(video, "transcription") else None,
        "summary": (
            video.transcription.summary
            if hasattr(video, "transcription")
            and video.transcription
            and hasattr(video.transcription, "summary")
            else None
        ),
    }

    return VideoDetailResponse(**response_data)


@router.patch(
    "/{video_id}",
    response_model=VideoResponse,
    summary="Update video",
    description="Update video metadata (title, duration, metadata).",
    responses={
        200: {"description": "Video updated successfully"},
        400: {
            "description": "No fields provided to update",
            "content": {
                "application/json": {
                    "example": {"detail": "At least one field must be provided to update"}
                }
            },
        },
        404: {"description": "Video not found"},
    },
)
def update_video(
    video_id: UUID,
    video_repo: VideoRepo,
    title: str | None = Query(None, description="New title"),
    duration_seconds: int | None = Query(None, gt=0, description="New duration"),
) -> VideoResponse:
    """
    Actualizar metadata de un video.

    Args:
        video_id: UUID del video.
        title: Nuevo titulo (opcional).
        duration_seconds: Nueva duracion (opcional).
        video_repo: Repositorio de videos (inyectado).

    Returns:
        VideoResponse: Video actualizado.

    Raises:
        VideoNotFoundError: Si el video no existe.
        HTTPException 400: Si no se proporciona ningun campo para actualizar.

    Example:
        PATCH /api/v1/videos/123e4567-e89b-12d3-a456-426614174000?title=New%20Title
    """
    video = video_repo.get_by_id(video_id)
    if not video:
        raise VideoNotFoundError(f"Video {video_id} not found")

    # Verificar que al menos un campo fue proporcionado
    if title is None and duration_seconds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )

    # Actualizar campos
    updates = {}
    if title is not None:
        updates["title"] = title
    if duration_seconds is not None:
        updates["duration_seconds"] = duration_seconds

    updated_video = video_repo.update_video(video_id, **updates)
    return VideoResponse.model_validate(updated_video)


@router.delete(
    "/{video_id}",
    response_model=MessageResponse,
    summary="Delete video",
    description="Soft delete a video (sets deleted_at timestamp).",
    responses={
        200: {
            "description": "Video deleted successfully",
            "content": {"application/json": {"example": {"message": "Video deleted successfully"}}},
        },
        400: {"description": "Video already deleted"},
        404: {"description": "Video not found"},
    },
)
def delete_video(
    video_id: UUID,
    video_repo: VideoRepo,
    current_user: Annotated[User, Depends(require_admin)],
) -> MessageResponse:
    """
    Soft delete de un video.

    Args:
        video_id: UUID del video.
        video_repo: Repositorio de videos (inyectado).

    Returns:
        MessageResponse: Confirmacion de eliminacion.

    Raises:
        VideoNotFoundError: Si el video no existe.
        HTTPException 400: Si el video ya esta eliminado.

    Example:
        DELETE /api/v1/videos/123e4567-e89b-12d3-a456-426614174000
    """
    video = video_repo.get_by_id(video_id)
    if not video:
        raise VideoNotFoundError(f"Video {video_id} not found")

    if video.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video {video_id} is already deleted",
        )

    # Soft delete
    video_repo.soft_delete(video_id)
    return MessageResponse(message=f"Video {video_id} deleted successfully")


@router.post(
    "/{video_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProcessVideoResponse,
    summary="Process video",
    description="Enqueue video for processing (download, transcribe, summarize).",
    responses={
        202: {
            "description": "Video queued for processing",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Video queued for processing",
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
        404: {"description": "Video not found"},
        409: {
            "description": "Video in invalid state for processing",
            "content": {
                "application/json": {
                    "example": {"detail": "Video is already completed or in progress"}
                }
            },
        },
    },
)
@limiter.limit("3/minute")  # Límite más restrictivo para procesamiento (costoso)
def process_video(
    request: Request,
    video_id: UUID,
    video_repo: VideoRepo,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProcessVideoResponse:
    """
    Encolar video para procesamiento.

    Args:
        video_id: UUID del video.
        video_repo: Repositorio de videos (inyectado).

    Returns:
        ProcessVideoResponse: ID de la tarea Celery.

    Raises:
        VideoNotFoundError: Si el video no existe.
        InvalidVideoStateError: Si el video no esta en estado procesable.

    Example:
        POST /api/v1/videos/123e4567-e89b-12d3-a456-426614174000/process
    """
    video = video_repo.get_by_id(video_id)
    if not video:
        raise VideoNotFoundError(f"Video {video_id} not found")

    # Validar estado
    if video.status not in {VideoStatus.PENDING, VideoStatus.FAILED}:
        raise InvalidVideoStateError(
            f"Video {video_id} is in state '{video.status.value}', "
            "only 'pending' or 'failed' videos can be processed"
        )

    # Encolar tarea
    task = process_video_task.delay(str(video_id))

    return ProcessVideoResponse(
        task_id=task.id,
        video_id=video_id,
        message=f"Video {video_id} enqueued for processing",
    )


@router.post(
    "/{video_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProcessVideoResponse,
    summary="Retry failed video",
    description="Retry processing a failed video.",
)
def retry_video(
    video_id: UUID,
    video_repo: VideoRepo,
) -> ProcessVideoResponse:
    """
    Reintentar procesamiento de un video fallido.

    Args:
        video_id: UUID del video.
        video_repo: Repositorio de videos (inyectado).

    Returns:
        ProcessVideoResponse: ID de la tarea Celery.

    Raises:
        VideoNotFoundError: Si el video no existe.
        InvalidVideoStateError: Si el video no esta en estado 'failed'.

    Example:
        POST /api/v1/videos/123e4567-e89b-12d3-a456-426614174000/retry
    """
    video = video_repo.get_by_id(video_id)
    if not video:
        raise VideoNotFoundError(f"Video {video_id} not found")

    # Validar estado
    if video.status != VideoStatus.FAILED:
        raise InvalidVideoStateError(
            f"Video {video_id} is in state '{video.status.value}', "
            "only 'failed' videos can be retried"
        )

    # Encolar tarea de retry
    task = retry_failed_video_task.delay(str(video_id))

    return ProcessVideoResponse(
        task_id=task.id,
        video_id=video_id,
        message=f"Video {video_id} enqueued for retry",
    )


@router.get(
    "/{video_id}/stats",
    response_model=VideoStatsResponse,
    summary="Get video statistics",
    description="Get processing statistics for a specific video.",
)
def get_video_stats(
    video_id: UUID,
    video_repo: VideoRepo,
    db: DBSession,
) -> VideoStatsResponse:
    """
    Obtener estadisticas de un video.

    Args:
        video_id: UUID del video.
        video_repo: Repositorio de videos (inyectado).
        db: Sesion de BD (inyectada).

    Returns:
        VideoStatsResponse: Estadisticas del video.

    Raises:
        VideoNotFoundError: Si el video no existe.

    Example:
        GET /api/v1/videos/123e4567-e89b-12d3-a456-426614174000/stats
    """
    video = video_repo.get_by_id(video_id)
    if not video:
        raise VideoNotFoundError(f"Video {video_id} not found")

    # Calcular estadisticas
    transcription_word_count = None
    summary_key_points_count = None
    processing_time_seconds = None

    if hasattr(video, "transcription") and video.transcription:
        transcription_word_count = video.transcription.word_count

        if hasattr(video.transcription, "summary") and video.transcription.summary:
            # NOTE: Summary model doesn't have key_points field yet, using keywords count as proxy
            summary_key_points_count = len(video.transcription.summary.keywords or [])

    # Calcular tiempo de procesamiento (created_at -> updated_at)
    if video.status == VideoStatus.COMPLETED:
        processing_time_seconds = (video.updated_at - video.created_at).total_seconds()

    return VideoStatsResponse(
        video_id=video_id,
        duration_seconds=video.duration_seconds,
        transcription_word_count=transcription_word_count,
        summary_key_points_count=summary_key_points_count,
        processing_time_seconds=processing_time_seconds,
    )


@router.get(
    "/{video_id}/transcription",
    response_model=TranscriptionResponse,
    summary="Get video transcription",
    description="Get the transcription for a specific video.",
)
def get_video_transcription(
    video_id: UUID,
    video_repo: VideoRepo,
    transcription_repo: TranscriptionRepo,
) -> TranscriptionResponse:
    """
    Obtener transcripcion de un video especifico.

    Este endpoint es un atajo para acceder a la transcripcion
    directamente desde el ID del video.

    Args:
        video_id: UUID del video.
        video_repo: Repositorio de videos (inyectado).
        transcription_repo: Repositorio de transcripciones (inyectado).

    Returns:
        TranscriptionResponse: Transcripcion del video.

    Raises:
        VideoNotFoundError: Si el video no existe.
        HTTPException 404: Si el video no tiene transcripcion.

    Example:
        GET /api/v1/videos/123e4567-e89b-12d3-a456-426614174000/transcription
    """
    # Verificar que el video existe
    video = video_repo.get_by_id(video_id)
    if not video:
        raise VideoNotFoundError(f"Video {video_id} not found")

    # Buscar transcripcion por video_id
    transcription = transcription_repo.get_by_video_id(video_id)
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} does not have a transcription yet",
        )

    return TranscriptionResponse.model_validate(transcription)


@router.get(
    "/{video_id}/summary",
    response_model=SummaryResponse,
    summary="Get video summary",
    description="Get the AI-generated summary for a specific video.",
)
def get_video_summary(
    video_id: UUID,
    video_repo: VideoRepo,
    summary_repo: SummaryRepo,
) -> SummaryResponse:
    """
    Obtener resumen de un video especifico.

    Este endpoint es un atajo para acceder al resumen
    directamente desde el ID del video.

    Args:
        video_id: UUID del video.
        video_repo: Repositorio de videos (inyectado).
        summary_repo: Repositorio de resumenes (inyectado).

    Returns:
        SummaryResponse: Resumen del video.

    Raises:
        VideoNotFoundError: Si el video no existe.
        HTTPException 404: Si el video no tiene resumen.

    Example:
        GET /api/v1/videos/123e4567-e89b-12d3-a456-426614174000/summary
    """
    # Verificar que el video existe
    video = video_repo.get_by_id(video_id)
    if not video:
        raise VideoNotFoundError(f"Video {video_id} not found")

    # Buscar resumen por video_id
    summary = summary_repo.get_by_video_id(video_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} does not have a summary yet",
        )

    return SummaryResponse.model_validate(summary)
