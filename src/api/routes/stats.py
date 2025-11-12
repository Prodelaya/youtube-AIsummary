"""
Router de Stats - Endpoints para estadisticas del sistema.

Este modulo define 2 endpoints para metricas y estadisticas:
1. GET /stats                    - Estadisticas globales del sistema
2. GET /stats/sources/{source_id} - Estadisticas de una fuente especifica

Las estadisticas incluyen contadores de videos por estado, transcripciones,
resumenes, y metricas de procesamiento agrupadas por fuente.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.dependencies import DBSession, SourceRepo
from src.api.schemas.stats import (
    GlobalStatsResponse,
    SourceStats,
    SourceStatsResponse,
)
from src.models import Source, Summary, Transcription, Video
from src.models.video import VideoStatus

# ==================== ROUTER ====================

router = APIRouter(prefix="/stats", tags=["Stats"])


# ==================== ENDPOINTS ====================


@router.get(
    "",
    response_model=GlobalStatsResponse,
    summary="Get global statistics",
    description="Get system-wide statistics including video counts, transcriptions, and summaries.",
    responses={
        200: {
            "description": "Global statistics",
            "content": {
                "application/json": {
                    "example": {
                        "total_videos": 150,
                        "completed_videos": 120,
                        "failed_videos": 10,
                        "pending_videos": 20,
                        "total_transcriptions": 120,
                        "total_summaries": 115,
                        "sources": [
                            {
                                "source_id": "123e4567-e89b-12d3-a456-426614174000",
                                "source_name": "DotCSV",
                                "total_videos": 50,
                                "completed_videos": 45,
                                "failed_videos": 2,
                                "pending_videos": 3
                            }
                        ]
                    }
                }
            }
        }
    }
)
def get_global_stats(
    db: DBSession,
) -> GlobalStatsResponse:
    """
    Obtener estadisticas globales del sistema.

    Calcula contadores agregados de todos los videos, transcripciones
    y resumenes, con desglose por estado y por fuente.

    Args:
        db: Sesion de BD (inyectada).

    Returns:
        GlobalStatsResponse: Estadisticas globales con desglose por fuente.

    Example:
        GET /api/v1/stats
    """
    # Contadores globales
    total_videos = db.query(func.count(Video.id)).scalar() or 0
    completed_videos = (
        db.query(func.count(Video.id))
        .filter(Video.status == VideoStatus.COMPLETED)
        .scalar()
        or 0
    )
    failed_videos = (
        db.query(func.count(Video.id))
        .filter(Video.status == VideoStatus.FAILED)
        .scalar()
        or 0
    )
    pending_videos = (
        db.query(func.count(Video.id))
        .filter(Video.status == VideoStatus.PENDING)
        .scalar()
        or 0
    )

    total_transcriptions = db.query(func.count(Transcription.id)).scalar() or 0
    total_summaries = db.query(func.count(Summary.id)).scalar() or 0

    # Estadisticas por fuente
    sources = db.query(Source).all()
    source_stats_list = []

    for source in sources:
        source_total = (
            db.query(func.count(Video.id))
            .filter(Video.source_id == source.id)
            .scalar()
            or 0
        )
        source_completed = (
            db.query(func.count(Video.id))
            .filter(Video.source_id == source.id, Video.status == VideoStatus.COMPLETED)
            .scalar()
            or 0
        )
        source_failed = (
            db.query(func.count(Video.id))
            .filter(Video.source_id == source.id, Video.status == VideoStatus.FAILED)
            .scalar()
            or 0
        )
        source_pending = (
            db.query(func.count(Video.id))
            .filter(Video.source_id == source.id, Video.status == VideoStatus.PENDING)
            .scalar()
            or 0
        )

        source_stats_list.append(
            SourceStats(
                source_id=source.id,
                source_name=source.name,
                total_videos=source_total,
                completed_videos=source_completed,
                failed_videos=source_failed,
                pending_videos=source_pending,
            )
        )

    return GlobalStatsResponse(
        total_videos=total_videos,
        completed_videos=completed_videos,
        failed_videos=failed_videos,
        pending_videos=pending_videos,
        total_transcriptions=total_transcriptions,
        total_summaries=total_summaries,
        sources=source_stats_list,
    )


@router.get(
    "/sources/{source_id}",
    response_model=SourceStatsResponse,
    summary="Get source statistics",
    description="Get detailed statistics for a specific source.",
    responses={
        200: {
            "description": "Source statistics",
            "content": {
                "application/json": {
                    "example": {
                        "source_id": "123e4567-e89b-12d3-a456-426614174000",
                        "source_name": "DotCSV",
                        "total_videos": 50,
                        "completed_videos": 45,
                        "failed_videos": 2,
                        "pending_videos": 3,
                        "avg_processing_time_seconds": 325.5,
                        "total_transcription_words": 125000
                    }
                }
            }
        },
        404: {"description": "Source not found"}
    }
)
def get_source_stats(
    source_id: UUID,
    db: DBSession,
    source_repo: SourceRepo,
) -> SourceStatsResponse:
    """
    Obtener estadisticas detalladas de una fuente.

    Incluye contadores de videos por estado, tiempo promedio de procesamiento
    y total de palabras transcritas.

    Args:
        source_id: UUID de la fuente.
        db: Sesion de BD (inyectada).
        source_repo: Repositorio de fuentes (inyectado).

    Returns:
        SourceStatsResponse: Estadisticas detalladas de la fuente.

    Raises:
        HTTPException 404: Si la fuente no existe.

    Example:
        GET /api/v1/stats/sources/123e4567-e89b-12d3-a456-426614174000
    """
    # Verificar que la fuente existe
    source = source_repo.get_by_id(source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} not found",
        )

    # Contadores por estado
    total_videos = (
        db.query(func.count(Video.id)).filter(Video.source_id == source_id).scalar()
        or 0
    )
    completed_videos = (
        db.query(func.count(Video.id))
        .filter(Video.source_id == source_id, Video.status == VideoStatus.COMPLETED)
        .scalar()
        or 0
    )
    failed_videos = (
        db.query(func.count(Video.id))
        .filter(Video.source_id == source_id, Video.status == VideoStatus.FAILED)
        .scalar()
        or 0
    )
    pending_videos = (
        db.query(func.count(Video.id))
        .filter(Video.source_id == source_id, Video.status == VideoStatus.PENDING)
        .scalar()
        or 0
    )

    # Tiempo promedio de procesamiento (solo videos completados)
    avg_processing_time = None
    if completed_videos > 0:
        # Calcular diferencia entre created_at y updated_at
        avg_seconds = (
            db.query(
                func.avg(
                    func.extract(
                        "epoch",
                        Video.updated_at - Video.created_at,
                    )
                )
            )
            .filter(Video.source_id == source_id, Video.status == VideoStatus.COMPLETED)
            .scalar()
        )
        if avg_seconds:
            avg_processing_time = float(avg_seconds)

    # Total de palabras transcritas
    # NOTE: word_count es un @property, no una columna de BD
    # Necesitamos calcular la suma extrayendo las transcripciones
    total_transcription_words = None
    transcriptions = (
        db.query(Transcription)
        .select_from(Video)
        .join(Transcription, Video.id == Transcription.video_id)
        .filter(Video.source_id == source_id)
        .all()
    )
    if transcriptions:
        total_transcription_words = sum(t.word_count for t in transcriptions)

    return SourceStatsResponse(
        source_id=source_id,
        source_name=source.name,
        total_videos=total_videos,
        completed_videos=completed_videos,
        failed_videos=failed_videos,
        pending_videos=pending_videos,
        avg_processing_time_seconds=avg_processing_time,
        total_transcription_words=total_transcription_words,
    )
