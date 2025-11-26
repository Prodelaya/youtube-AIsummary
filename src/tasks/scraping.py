"""
Tareas de Celery para scraping automático de nuevos videos de YouTube.

Este módulo contiene las tareas programadas que detectan automáticamente
nuevos videos de los canales suscritos y los encolan para procesamiento.

Tareas:
    - sync_youtube_sources_task: Escanea todos los canales activos de YouTube,
      detecta nuevos videos y los encola automáticamente.

Uso:
    # Ejecutar manualmente
    from src.tasks.scraping import sync_youtube_sources_task
    sync_youtube_sources_task.delay()

    # Celery Beat (automático cada 6 horas)
    Configurado en src/core/celery_app.py
"""

import logging
import uuid
from datetime import datetime

from celery import Task
from sqlalchemy.orm import Session

from src.core.celery_app import celery_app
from src.core.database import SessionLocal
from src.models.source import Source
from src.models.video import Video
from src.repositories.source_repository import SourceRepository
from src.repositories.video_repository import VideoRepository
from src.services.youtube_scraper_service import (
    ChannelUnavailableError,
    InvalidChannelURLError,
    RateLimitError,
    VideoMetadata,
    YouTubeScraperError,
    YouTubeScraperService,
)
from src.tasks.video_processing import process_video_task

logger = logging.getLogger(__name__)


# ==================== TAREA PRINCIPAL ====================


@celery_app.task(
    name="sync_youtube_sources",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutos entre reintentos
    time_limit=1800,  # 30 minutos timeout total
    soft_time_limit=1600,  # 26 minutos warning
)
def sync_youtube_sources_task(self: Task) -> dict:
    """
    Tarea programada que sincroniza nuevos videos de canales de YouTube.

    Flujo:
        1. Obtiene todas las fuentes activas con type='youtube_channel'
        2. Para cada fuente:
           a. Scraping de últimos 10 videos (metadata solamente)
           b. Verifica si ya existen en BD (por URL)
           c. Si son nuevos, crea registro con status='pending'
           d. Encola procesamiento automático con process_video_task
        3. Retorna estadísticas: fuentes, videos encontrados, videos nuevos

    Returns:
        dict: Estadísticas de la ejecución {
            'sources_scanned': int,
            'videos_found': int,
            'videos_new': int,
            'videos_enqueued': int,
            'errors': int
        }

    Raises:
        No lanza excepciones. Todos los errores son capturados y logueados.

    Example:
        >>> from src.tasks.scraping import sync_youtube_sources_task
        >>> result = sync_youtube_sources_task.delay()
        >>> result.get()  # Espera el resultado
        {'sources_scanned': 3, 'videos_found': 30, 'videos_new': 5, ...}
    """
    logger.info("🔄 Iniciando sync_youtube_sources_task")

    db: Session = SessionLocal()
    try:
        # Inicializar servicios
        scraper = YouTubeScraperService()
        source_repo = SourceRepository(db)
        video_repo = VideoRepository(db)

        # Obtener fuentes activas de YouTube
        sources: list[Source] = source_repo.get_by_type(
            source_type="youtube_channel", active_only=True
        )

        if not sources:
            logger.warning("⚠️ No hay fuentes de YouTube activas")
            return {
                "sources_scanned": 0,
                "videos_found": 0,
                "videos_new": 0,
                "videos_enqueued": 0,
                "errors": 0,
            }

        logger.info(f"📺 {len(sources)} fuentes de YouTube activas encontradas")

        # Estadísticas
        stats = {
            "sources_scanned": 0,
            "videos_found": 0,
            "videos_new": 0,
            "videos_enqueued": 0,
            "errors": 0,
        }

        # Procesar cada fuente
        for source in sources:
            try:
                logger.info(f"🔍 Scraping fuente: {source.name} ({source.url})")

                # Scraping de últimos 10 videos
                videos: list[VideoMetadata] = scraper.get_latest_videos(
                    channel_url=source.url, limit=10
                )

                stats["sources_scanned"] += 1
                stats["videos_found"] += len(videos)

                logger.info(f"📹 {len(videos)} videos encontrados en {source.name}")

                # Procesar cada video
                for video_meta in videos:
                    try:
                        # Verificar si ya existe (deduplicación por URL)
                        existing = video_repo.get_by_url(video_meta.url)

                        if existing:
                            logger.debug(f"⏭️ Video ya existe: {video_meta.title[:50]}...")
                            continue

                        # Crear nuevo video
                        new_video = _create_video_from_metadata(video_meta, source.id)
                        db.add(new_video)
                        db.flush()  # Obtener el ID sin commit

                        stats["videos_new"] += 1

                        logger.info(f"✅ Nuevo video detectado: {new_video.title[:60]}...")

                        # Encolar procesamiento automático
                        process_video_task.delay(str(new_video.id))
                        stats["videos_enqueued"] += 1

                        logger.info(f"📤 Video encolado para procesamiento: {new_video.id}")

                    except Exception as e:
                        logger.error(f"❌ Error procesando video {video_meta.video_id}: {e}")
                        stats["errors"] += 1
                        continue

                # Commit después de procesar todos los videos de una fuente
                db.commit()
                logger.info(f"💾 Cambios guardados para fuente: {source.name}")

            except InvalidChannelURLError as e:
                logger.error(f"❌ URL inválida para {source.name}: {e}")
                stats["errors"] += 1
                # TODO: Marcar fuente como inactiva?
                continue

            except ChannelUnavailableError as e:
                logger.warning(f"⚠️ Canal no disponible {source.name}: {e}")
                stats["errors"] += 1
                # TODO: Marcar fuente como inactiva?
                continue

            except RateLimitError as e:
                logger.error(f"🚫 Rate limit alcanzado para {source.name}: {e}")
                stats["errors"] += 1
                # Reintento con backoff exponencial
                raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

            except YouTubeScraperError as e:
                logger.error(f"❌ Error scraping {source.name}: {e}")
                stats["errors"] += 1
                continue

            except Exception as e:
                logger.exception(f"❌ Error inesperado procesando fuente {source.name}: {e}")
                stats["errors"] += 1
                continue

        logger.info(
            f"🎉 sync_youtube_sources_task completada. "
            f"Fuentes: {stats['sources_scanned']}, "
            f"Videos encontrados: {stats['videos_found']}, "
            f"Videos nuevos: {stats['videos_new']}, "
            f"Videos encolados: {stats['videos_enqueued']}, "
            f"Errores: {stats['errors']}"
        )

        return stats

    except Exception as e:
        logger.exception(f"❌ Error fatal en sync_youtube_sources_task: {e}")
        db.rollback()
        raise

    finally:
        db.close()


# ==================== HELPERS ====================


def _create_video_from_metadata(meta: VideoMetadata, source_id: uuid.UUID) -> Video:
    """
    Crea una instancia de Video desde VideoMetadata.

    Args:
        meta: Metadata del video desde yt-dlp
        source_id: UUID de la fuente (Source)

    Returns:
        Video: Instancia de Video con status='pending'
    """
    return Video(
        id=uuid.uuid4(),
        source_id=source_id,
        youtube_id=meta.video_id,
        title=meta.title,
        url=meta.url,
        duration_seconds=meta.duration_seconds,
        status="pending",
        published_at=meta.published_at,
        extra_metadata={
            "view_count": meta.view_count,
            "like_count": meta.like_count,
            "channel_name": meta.channel_name,
            "thumbnail_url": meta.thumbnail_url,
            "scraped_at": datetime.utcnow().isoformat(),
        },
    )
