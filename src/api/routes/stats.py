"""
Router de Stats - Endpoints para estadisticas del sistema.

Este modulo define 2 endpoints para metricas y estadisticas:
1. GET /stats                    - Estadisticas globales del sistema
2. GET /stats/sources/{source_id} - Estadisticas de una fuente especifica

Las estadisticas incluyen contadores de videos por estado, transcripciones,
resumenes, y metricas de procesamiento agrupadas por fuente.

CACHE:
- GET /stats: TTL 15 minutos (stats:global)
- GET /stats/sources/{source_id}: TTL 15 minutos (stats:source:{source_id})
- Headers: X-Cache-Status (HIT/MISS), X-Cache-TTL
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Response, status
from sqlalchemy import func

from src.api.dependencies import DBSession, SourceRepo
from src.api.schemas.stats import (
    GlobalStatsResponse,
    SourceStats,
    SourceStatsResponse,
)
from src.models import Source, Summary, Transcription, Video
from src.models.video import VideoStatus

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================

router = APIRouter(prefix="/stats", tags=["Stats"])


# ==================== ENDPOINTS ====================


@router.get(
    "",
    response_model=GlobalStatsResponse,
    summary="Get global statistics",
    description=(
        "Get system-wide statistics including video counts, transcriptions, and summaries. "
        "Results are cached for 15 minutes. Use header X-Cache-Bypass: true to force refresh."
    ),
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
                                "pending_videos": 3,
                            }
                        ],
                    }
                }
            },
        }
    },
)
def get_global_stats(
    response: Response,
    db: DBSession,
    x_cache_bypass: str | None = Header(None, alias="X-Cache-Bypass"),
) -> GlobalStatsResponse:
    """
    Obtener estadisticas globales del sistema.

    Calcula contadores agregados de todos los videos, transcripciones
    y resumenes, con desglose por estado y por fuente.

    Cache: 15 minutos (900 segundos)

    Args:
        response: FastAPI Response para añadir headers de caché.
        db: Sesion de BD (inyectada).
        x_cache_bypass: Header para forzar bypass de caché (opcional).

    Returns:
        GlobalStatsResponse: Estadisticas globales con desglose por fuente.

    Example:
        GET /api/v1/stats
        GET /api/v1/stats -H "X-Cache-Bypass: true"
    """
    # Import lazy para evitar importación circular
    from src.services.cache_service import cache_service

    cache_key = "stats:global"
    cache_ttl = 900  # 15 minutos

    # Determinar si se debe hacer bypass de caché
    bypass_cache = x_cache_bypass and x_cache_bypass.lower() in ("true", "1", "yes")

    # Intentar obtener de caché
    if not bypass_cache:
        cached_data = cache_service.get(cache_key, cache_type="stats")
        if cached_data:
            # Cache hit: retornar datos cacheados
            logger.info("Global stats cache HIT", extra={"cache_key": cache_key})
            response.headers["X-Cache-Status"] = "HIT"
            response.headers["X-Cache-TTL"] = str(
                cache_service.redis_client.ttl(cache_key) if cache_service.enabled else 0
            )

            # Reconstruir response desde datos cacheados
            return GlobalStatsResponse(**cached_data)

    # Cache miss o bypass: calcular estadísticas
    logger.info(
        "Global stats cache MISS or BYPASS",
        extra={"cache_key": cache_key, "bypass": bypass_cache},
    )

    # Contadores globales
    total_videos = db.query(func.count(Video.id)).scalar() or 0
    completed_videos = (
        db.query(func.count(Video.id)).filter(Video.status == VideoStatus.COMPLETED).scalar() or 0
    )
    failed_videos = (
        db.query(func.count(Video.id)).filter(Video.status == VideoStatus.FAILED).scalar() or 0
    )
    pending_videos = (
        db.query(func.count(Video.id)).filter(Video.status == VideoStatus.PENDING).scalar() or 0
    )

    total_transcriptions = db.query(func.count(Transcription.id)).scalar() or 0
    total_summaries = db.query(func.count(Summary.id)).scalar() or 0

    # Estadisticas por fuente
    sources = db.query(Source).all()
    source_stats_list = []

    for source in sources:
        source_total = (
            db.query(func.count(Video.id)).filter(Video.source_id == source.id).scalar() or 0
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

    # Construir response
    stats_response = GlobalStatsResponse(
        total_videos=total_videos,
        completed_videos=completed_videos,
        failed_videos=failed_videos,
        pending_videos=pending_videos,
        total_transcriptions=total_transcriptions,
        total_summaries=total_summaries,
        sources=source_stats_list,
    )

    # Cachear resultado (convertir a dict para serialización)
    cache_service.set(
        cache_key,
        stats_response.model_dump(),
        ttl=cache_ttl,
        cache_type="stats",
    )

    # Headers de caché
    response.headers["X-Cache-Status"] = "MISS"
    response.headers["X-Cache-TTL"] = str(cache_ttl)

    return stats_response


@router.get(
    "/sources/{source_id}",
    response_model=SourceStatsResponse,
    summary="Get source statistics",
    description=(
        "Get detailed statistics for a specific source. "
        "Results are cached for 15 minutes. Use header X-Cache-Bypass: true to force refresh."
    ),
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
                        "total_transcription_words": 125000,
                    }
                }
            },
        },
        404: {"description": "Source not found"},
    },
)
def get_source_stats(
    source_id: UUID,
    response: Response,
    db: DBSession,
    source_repo: SourceRepo,
    x_cache_bypass: str | None = Header(None, alias="X-Cache-Bypass"),
) -> SourceStatsResponse:
    """
    Obtener estadisticas detalladas de una fuente.

    Incluye contadores de videos por estado, tiempo promedio de procesamiento
    y total de palabras transcritas.

    Cache: 15 minutos (900 segundos)

    Args:
        source_id: UUID de la fuente.
        response: FastAPI Response para añadir headers de caché.
        db: Sesion de BD (inyectada).
        source_repo: Repositorio de fuentes (inyectado).
        x_cache_bypass: Header para forzar bypass de caché (opcional).

    Returns:
        SourceStatsResponse: Estadisticas detalladas de la fuente.

    Raises:
        HTTPException 404: Si la fuente no existe.

    Example:
        GET /api/v1/stats/sources/123e4567-e89b-12d3-a456-426614174000
        GET /api/v1/stats/sources/{id} -H "X-Cache-Bypass: true"
    """
    # Import lazy para evitar importación circular
    from src.services.cache_service import cache_service

    # Verificar que la fuente existe (esto siempre se ejecuta, incluso con caché)
    source = source_repo.get_by_id(source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} not found",
        )

    cache_key = f"stats:source:{source_id}"
    cache_ttl = 900  # 15 minutos

    # Determinar si se debe hacer bypass de caché
    bypass_cache = x_cache_bypass and x_cache_bypass.lower() in ("true", "1", "yes")

    # Intentar obtener de caché
    if not bypass_cache:
        cached_data = cache_service.get(cache_key, cache_type="stats")
        if cached_data:
            # Cache hit: retornar datos cacheados
            logger.info(
                "Source stats cache HIT",
                extra={"cache_key": cache_key, "source_id": str(source_id)},
            )
            response.headers["X-Cache-Status"] = "HIT"
            response.headers["X-Cache-TTL"] = str(
                cache_service.redis_client.ttl(cache_key) if cache_service.enabled else 0
            )

            # Reconstruir response desde datos cacheados
            return SourceStatsResponse(**cached_data)

    # Cache miss o bypass: calcular estadísticas
    logger.info(
        "Source stats cache MISS or BYPASS",
        extra={"cache_key": cache_key, "source_id": str(source_id), "bypass": bypass_cache},
    )

    # Contadores por estado
    total_videos = db.query(func.count(Video.id)).filter(Video.source_id == source_id).scalar() or 0
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

    # Construir response
    source_stats_response = SourceStatsResponse(
        source_id=source_id,
        source_name=source.name,
        total_videos=total_videos,
        completed_videos=completed_videos,
        failed_videos=failed_videos,
        pending_videos=pending_videos,
        avg_processing_time_seconds=avg_processing_time,
        total_transcription_words=total_transcription_words,
    )

    # Cachear resultado (convertir a dict para serialización)
    cache_service.set(
        cache_key,
        source_stats_response.model_dump(),
        ttl=cache_ttl,
        cache_type="stats",
    )

    # Headers de caché
    response.headers["X-Cache-Status"] = "MISS"
    response.headers["X-Cache-TTL"] = str(cache_ttl)

    return source_stats_response


@router.get(
    "/videos/skipped",
    response_model=dict,
    summary="Get skipped videos statistics",
    description="Get videos that were skipped due to exceeding duration limit or other criteria.",
    responses={
        200: {
            "description": "Skipped videos statistics",
            "content": {
                "application/json": {
                    "example": {
                        "total_skipped": 15,
                        "breakdown": {"duration_exceeded": 15},
                        "videos": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "youtube_id": "dQw4w9WgXcQ",
                                "title": "Long Video Title",
                                "duration_seconds": 3600,
                                "duration_formatted": "1:00:00",
                                "skip_reason": "duration_exceeded",
                                "skipped_at": "2025-11-13T12:00:00Z",
                            }
                        ],
                    }
                }
            },
        },
    },
)
def get_skipped_videos_stats(
    db: DBSession,
    source_id: UUID | None = None,
) -> dict:
    """
    Estadísticas de videos descartados por duración u otros criterios.

    Permite analizar qué contenido no se está procesando y por qué.
    Útil para ajustar el límite de duración o identificar patrones.

    Args:
        db: Sesión de BD (inyectada).
        source_id: Filtrar por fuente específica (opcional).

    Returns:
        dict: Estadísticas y lista de videos descartados.

    Example:
        GET /api/v1/stats/videos/skipped
        GET /api/v1/stats/videos/skipped?source_id=123e4567-e89b-12d3-a456-426614174000
    """
    from src.bot.utils.formatters import format_duration

    query = db.query(Video).filter(Video.status == VideoStatus.SKIPPED)

    if source_id:
        query = query.filter(Video.source_id == source_id)

    skipped_videos = query.order_by(Video.created_at.desc()).limit(50).all()

    return {
        "total_skipped": len(skipped_videos),
        "breakdown": {
            "duration_exceeded": sum(
                1
                for v in skipped_videos
                if v.extra_metadata and v.extra_metadata.get("skip_reason") == "duration_exceeded"
            )
        },
        "videos": [
            {
                "id": str(v.id),
                "youtube_id": v.youtube_id,
                "title": v.title,
                "duration_seconds": v.duration_seconds,
                "duration_formatted": (
                    format_duration(v.duration_seconds) if v.duration_seconds else None
                ),
                "skip_reason": v.extra_metadata.get("skip_reason") if v.extra_metadata else None,
                "skipped_at": v.extra_metadata.get("skipped_at") if v.extra_metadata else None,
            }
            for v in skipped_videos
        ],
    }
