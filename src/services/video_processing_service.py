"""
Servicio de orquestación del pipeline completo de procesamiento de videos.

Este módulo coordina el flujo end-to-end desde la URL de YouTube hasta
el resumen final guardado en la base de datos:

URL → Metadata → Download Audio → Transcribe → Summarize → Save to DB → Cleanup

El servicio implementa:
- Arquitectura 100% asíncrona (preparada para Celery)
- Máquina de estados del video con transiciones seguras
- Commits intermedios para preservar trabajo costoso
- Logging estructurado con contexto de video_id
- Gestión automática de archivos temporales
- Manejo robusto de errores con estados de fallo específicos
"""

import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.logging_config import get_logger
from src.core.metrics import metrics
from src.models import Summary, Transcription, Video
from src.models.video import VideoStatus
from src.repositories.transcription_repository import TranscriptionRepository
from src.repositories.video_repository import VideoRepository
from src.services.downloader_service import (
    AudioExtractionError,
    DownloaderService,
    InvalidURLError,
    NetworkError,
    VideoNotAvailableError,
)
from src.services.summarization_service import (
    DeepSeekAPIError,
    SummarizationService,
)
from src.services.transcription_service import (
    TranscriptionFailedError,
    get_transcription_service,
)

# ==================== LOGGER ====================

logger = get_logger(__name__)


# ==================== EXCEPCIONES PERSONALIZADAS ====================


class VideoProcessingError(Exception):
    """Excepción base para errores del pipeline de procesamiento."""

    pass


class VideoNotFoundError(VideoProcessingError):
    """El video no existe en la base de datos."""

    pass


class InvalidVideoStateError(VideoProcessingError):
    """El video no está en un estado válido para procesamiento."""

    pass


# ==================== SERVICIO ORQUESTADOR ====================


class VideoProcessingService:
    """
    Orquestador del pipeline completo de procesamiento de videos.

    Este servicio coordina la ejecución secuencial de todos los pasos
    necesarios para procesar un video de YouTube:

    1. Validación del video en BD
    2. Obtención de metadata de YouTube
    3. Descarga de audio en formato MP3
    4. Transcripción con Whisper
    5. Generación de resumen con DeepSeek
    6. Limpieza de archivos temporales

    El servicio gestiona automáticamente:
    - Estados intermedios del video (downloading, transcribing, summarizing)
    - Commits incrementales en BD (preservar trabajo costoso)
    - Logging estructurado con contexto del video
    - Manejo de errores con estados de fallo específicos
    - Limpieza de archivos temporales (éxito o error)

    Example:
        >>> service = VideoProcessingService()
        >>> video = await service.process_video(session, video_id)
        >>> print(f"Video procesado: {video.status}")
        'completed'
    """

    def __init__(self):
        """
        Inicializa el servicio de procesamiento.

        Los servicios dependientes se crean como instancias singleton
        para reutilizar modelos cargados (Whisper, etc.).
        """
        self.downloader = DownloaderService()
        self.transcriber = get_transcription_service()
        self.summarizer = SummarizationService()

        logger.info("video_processing_service_initialized")

    async def process_video(
        self,
        session: Session,
        video_id: UUID,
    ) -> Video:
        """
        Procesa un video completo end-to-end.

        Ejecuta todas las fases del pipeline: descarga, transcripción,
        resumen y limpieza. Actualiza el estado del video en cada paso
        y guarda progreso incremental en BD.

        Args:
            session: Sesión de SQLAlchemy para acceso a BD.
            video_id: UUID del video a procesar.

        Returns:
            Video con status="completed" y todas las relaciones cargadas.

        Raises:
            VideoNotFoundError: Si el video no existe en BD.
            InvalidVideoStateError: Si el video no está en estado procesable.
            InvalidURLError: Si la URL del video es inválida.
            VideoNotAvailableError: Si el video no está disponible en YouTube.
            NetworkError: Si falla la descarga por problemas de red.
            TranscriptionFailedError: Si falla la transcripción con Whisper.
            DeepSeekAPIError: Si falla la generación del resumen.

        Example:
            >>> service = VideoProcessingService()
            >>> video = await service.process_video(session, video_id)
            >>> print(video.status)
            VideoStatus.COMPLETED
        """
        # Inicializar repositorio
        video_repo = VideoRepository(session)

        # Validar que el video existe
        video = video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(f"Video {video_id} no encontrado en BD")

        # Validar que el video está en estado procesable
        if video.status not in {VideoStatus.PENDING, VideoStatus.FAILED}:
            raise InvalidVideoStateError(
                f"Video {video_id} está en estado '{video.status.value}', "
                f"solo se pueden procesar videos en estado 'pending' o 'failed'"
            )

        # ==================== VALIDACIÓN DE DURACIÓN ====================
        if video.duration_seconds and video.duration_seconds > settings.MAX_VIDEO_DURATION_SECONDS:
            logger.bind(
                video_id=str(video_id),
                youtube_id=video.youtube_id,
                title=video.title,
                duration_seconds=video.duration_seconds,
                max_allowed_seconds=settings.MAX_VIDEO_DURATION_SECONDS,
            ).warning("video_skipped_duration_exceeded")

            # Marcar como SKIPPED y guardar razón en metadata
            video.status = VideoStatus.SKIPPED
            video.extra_metadata = video.extra_metadata or {}
            video.extra_metadata.update(  # type: ignore
                {
                    "skip_reason": "duration_exceeded",
                    "max_allowed_seconds": settings.MAX_VIDEO_DURATION_SECONDS,
                    "actual_duration_seconds": video.duration_seconds,
                    "skipped_at": datetime.now(UTC).isoformat(),
                }
            )

            session.commit()

            # Métrica de video omitido
            metrics.videos_processed_total.labels(status="skipped").inc()

            # Formatear duraciones para el log final
            max_duration_formatted = self._format_duration(settings.MAX_VIDEO_DURATION_SECONDS)
            actual_duration_formatted = self._format_duration(video.duration_seconds)

            logger.bind(
                video_id=str(video_id),
                reason="duration_exceeded",
                duration=actual_duration_formatted,
                max_allowed=max_duration_formatted,
            ).info("video_marked_as_skipped")

            return video
        # ==================== FIN VALIDACIÓN ====================

        logger.bind(
            video_id=str(video.id),
            youtube_id=video.youtube_id,
            url=video.url,
            status=video.status.value,
        ).info("video_processing_started")

        audio_path: Path | None = None
        start_time_total = time.time()

        try:
            # ==================== FASE 1: DESCARGA ====================
            start_time_download = time.time()
            audio_path = await self._download_audio(session, video, video_repo)
            download_duration = time.time() - start_time_download
            metrics.video_processing_duration_seconds.labels(phase="download").observe(
                download_duration
            )

            # ==================== FASE 2: TRANSCRIPCIÓN ====================
            start_time_transcription = time.time()
            transcription = await self._transcribe_audio(session, video, audio_path, video_repo)
            transcription_duration = time.time() - start_time_transcription
            metrics.video_processing_duration_seconds.labels(phase="transcription").observe(
                transcription_duration
            )

            # ==================== FASE 3: RESUMEN ====================
            start_time_summary = time.time()
            summary = await self._create_summary(session, video, transcription, video_repo)
            summary_duration = time.time() - start_time_summary
            metrics.video_processing_duration_seconds.labels(phase="summary").observe(
                summary_duration
            )

            # ==================== FASE 4: DISTRIBUCIÓN ====================
            # Encolar tarea de distribución automática a usuarios suscritos
            from src.tasks.distribute_summaries import distribute_summary_task

            distribute_summary_task.delay(str(summary.id))

            logger.bind(
                video_id=str(video.id),
                summary_id=str(summary.id),
            ).info("distribution_task_enqueued")

            # ==================== COMPLETADO ====================
            video.status = VideoStatus.COMPLETED
            session.commit()

            # Métricas de éxito
            total_duration = time.time() - start_time_total
            metrics.video_processing_duration_seconds.labels(phase="total").observe(total_duration)
            metrics.videos_processed_total.labels(status="completed").inc()

            # Registrar duración del video procesado
            if video.duration_seconds:
                metrics.video_duration_seconds.observe(video.duration_seconds)

            logger.bind(
                video_id=str(video.id),
                transcription_id=str(transcription.id),
                summary_id=str(summary.id),
                status="completed",
                total_duration_seconds=round(total_duration, 2),
            ).info("video_processing_completed")

            # Limpiar archivos temporales después del éxito
            if audio_path:
                self._cleanup_audio_file(audio_path)

            return video

        except (InvalidURLError, VideoNotAvailableError) as e:
            # Errores de descarga (no recuperables)
            video.status = VideoStatus.FAILED
            session.commit()

            # Métricas de error
            metrics.videos_processed_total.labels(status="failed").inc()
            metrics.video_processing_errors_total.labels(error_type="download").inc()

            logger.bind(
                video_id=str(video.id),
                error=str(e),
                status="failed",
            ).error("video_processing_failed_download")
            raise

        except (NetworkError, AudioExtractionError) as e:
            # Errores de descarga (potencialmente recuperables)
            video.status = VideoStatus.FAILED
            session.commit()

            # Métricas de error
            metrics.videos_processed_total.labels(status="failed").inc()
            metrics.video_processing_errors_total.labels(error_type="download").inc()

            logger.bind(
                video_id=str(video.id),
                error=str(e),
                error_type=type(e).__name__,
                status="failed",
            ).error("video_processing_failed_download")

            # Intentar limpiar archivo parcial si existe
            if audio_path and audio_path.exists():
                self._cleanup_audio_file(audio_path)

            raise

        except TranscriptionFailedError as e:
            # Error de transcripción
            video.status = VideoStatus.FAILED
            session.commit()

            # Métricas de error
            metrics.videos_processed_total.labels(status="failed").inc()
            metrics.video_processing_errors_total.labels(error_type="transcription").inc()

            logger.bind(
                video_id=str(video.id),
                error=str(e),
                status="failed",
            ).error("video_processing_failed_transcription")

            # Mantener audio para debugging (no borrar)
            if audio_path:
                logger.bind(
                    video_id=str(video.id),
                    audio_path=str(audio_path),
                ).info("audio_file_kept_for_debugging")

            raise

        except DeepSeekAPIError as e:
            # Error de resumen
            video.status = VideoStatus.FAILED
            session.commit()

            # Métricas de error
            metrics.videos_processed_total.labels(status="failed").inc()
            metrics.video_processing_errors_total.labels(error_type="summary").inc()

            logger.bind(
                video_id=str(video.id),
                error=str(e),
                status_code=getattr(e, "status_code", None),
                status="failed",
            ).error("video_processing_failed_summarization")

            # Limpiar audio (transcripción ya está guardada)
            if audio_path:
                self._cleanup_audio_file(audio_path)

            raise

        except Exception as e:
            # Error inesperado
            video.status = VideoStatus.FAILED
            session.commit()

            # Métricas de error
            metrics.videos_processed_total.labels(status="failed").inc()
            metrics.video_processing_errors_total.labels(error_type="other").inc()

            logger.bind(
                video_id=str(video.id),
                error=str(e),
                error_type=type(e).__name__,
                status="failed",
            ).exception("video_processing_failed_unexpected")

            # Intentar limpiar archivo si existe
            if audio_path and audio_path.exists():
                self._cleanup_audio_file(audio_path)

            raise

    async def _download_audio(
        self,
        session: Session,
        video: Video,
        video_repo: VideoRepository,
    ) -> Path:
        """
        Descarga el audio del video de YouTube.

        Actualiza el estado del video a 'downloading' antes de iniciar
        y a 'downloaded' al completar exitosamente.

        Args:
            session: Sesión de SQLAlchemy.
            video: Objeto Video a procesar.
            video_repo: Repositorio de videos.

        Returns:
            Path al archivo MP3 descargado.

        Raises:
            InvalidURLError: URL inválida.
            VideoNotAvailableError: Video no disponible.
            NetworkError: Error de red.
            AudioExtractionError: Error al extraer audio.
        """
        # Actualizar estado
        video.status = VideoStatus.DOWNLOADING
        session.commit()

        logger.bind(
            video_id=str(video.id),
            url=video.url,
            status="downloading",
        ).info("audio_download_started")

        # Descargar audio (ya es async)
        audio_path = await self.downloader.download_audio(video.url)

        # Obtener tamaño del archivo
        file_size_bytes = audio_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Métricas de descarga
        metrics.audio_downloads_total.labels(status="success").inc()
        metrics.audio_file_size_bytes.observe(file_size_bytes)

        # Actualizar estado
        video.status = VideoStatus.DOWNLOADED
        session.commit()

        logger.bind(
            video_id=str(video.id),
            audio_path=str(audio_path),
            file_size_mb=round(file_size_mb, 2),
            file_size_bytes=file_size_bytes,
            status="downloaded",
        ).info("audio_downloaded")

        return audio_path

    async def _transcribe_audio(
        self,
        session: Session,
        video: Video,
        audio_path: Path,
        video_repo: VideoRepository,
    ) -> Transcription:
        """
        Transcribe el audio usando Whisper.

        Actualiza el estado del video a 'transcribing' antes de iniciar
        y a 'transcribed' al completar. Guarda la transcripción en BD.

        Args:
            session: Sesión de SQLAlchemy.
            video: Objeto Video a procesar.
            audio_path: Path al archivo MP3 a transcribir.
            video_repo: Repositorio de videos.

        Returns:
            Transcription creada y persistida en BD.

        Raises:
            TranscriptionFailedError: Si falla la transcripción.
        """
        # Actualizar estado
        video.status = VideoStatus.TRANSCRIBING
        session.commit()

        logger.bind(
            video_id=str(video.id),
            audio_path=str(audio_path),
            status="transcribing",
        ).info("transcription_started")

        # Transcribir (ejecutar en thread separado)
        result = await self.transcriber.transcribe_audio(audio_path)

        # Crear objeto Transcription
        transcription_repo = TranscriptionRepository(session)
        transcription = Transcription(
            video_id=video.id,
            text=result.text,
            language=result.language,
            model_used="whisper-base",
            duration_seconds=int(result.duration),
        )

        # Guardar en BD (commit intermedio)
        created_transcription = transcription_repo.create(transcription)
        session.commit()

        # Actualizar estado
        video.status = VideoStatus.TRANSCRIBED
        session.commit()

        # Métricas de transcripción
        metrics.transcriptions_total.labels(model="whisper-base", status="success").inc()
        metrics.transcription_text_length_chars.observe(len(result.text))

        logger.bind(
            video_id=str(video.id),
            transcription_id=str(created_transcription.id),
            text_length=len(result.text),
            language=result.language,
            duration_seconds=int(result.duration),
            status="transcribed",
        ).info("transcription_completed")

        return created_transcription

    async def _create_summary(
        self,
        session: Session,
        video: Video,
        transcription: Transcription,
        video_repo: VideoRepository,
    ) -> Summary:
        """
        Genera resumen con DeepSeek API.

        Actualiza el estado del video a 'summarizing' antes de iniciar.
        Guarda el resumen en BD.

        Args:
            session: Sesión de SQLAlchemy.
            video: Objeto Video a procesar.
            transcription: Transcripción del video.
            video_repo: Repositorio de videos.

        Returns:
            Summary creado y persistido en BD.

        Raises:
            DeepSeekAPIError: Si falla la API.
        """
        # Actualizar estado
        video.status = VideoStatus.SUMMARIZING
        session.commit()

        logger.bind(
            video_id=str(video.id),
            transcription_id=str(transcription.id),
            status="summarizing",
        ).info("summarization_started")

        # Generar resumen (ya es async)
        summary = await self.summarizer.generate_summary(session, transcription.id)

        # Commit ya se hace dentro de generate_summary
        # session.commit() ya ejecutado

        # Métricas de resumen
        metrics.summaries_generated_total.labels(status="success").inc()
        # Nota: Las métricas de AI API (tokens, cost) se registran en SummarizationService

        logger.bind(
            video_id=str(video.id),
            summary_id=str(summary.id),
            summary_length=len(summary.summary_text),
            keywords=summary.keywords,
            tokens_used=summary.tokens_used,
            status="summarizing",
        ).info("summary_created")

        return summary

    def _cleanup_audio_file(self, audio_path: Path) -> None:
        """
        Elimina el archivo de audio temporal.

        Se llama después de completar el pipeline exitosamente,
        o después de errores de red/descarga.

        Args:
            audio_path: Path al archivo MP3 a eliminar.
        """
        try:
            if audio_path.exists():
                audio_path.unlink()
                logger.bind(
                    audio_path=str(audio_path),
                ).info("audio_file_deleted")
            else:
                logger.bind(
                    audio_path=str(audio_path),
                ).warning("audio_file_not_found_for_cleanup")
        except Exception as e:
            # No fallar el pipeline por error de limpieza
            logger.bind(
                audio_path=str(audio_path),
                error=str(e),
            ).error("audio_file_cleanup_failed")

    def _format_duration(self, seconds: int) -> str:
        """
        Convierte segundos a formato legible HH:MM:SS o MM:SS.

        Args:
            seconds: Duración en segundos.

        Returns:
            String formateado (ej: "35:59", "1:02:15").

        Example:
            >>> service._format_duration(2159)
            '35:59'
            >>> service._format_duration(3665)
            '1:01:05'
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
