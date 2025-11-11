"""
Dependencias de FastAPI para inyeccion en endpoints.

Este modulo contiene funciones de dependencia que se usan en los endpoints:
- get_db: Proporciona sesion de base de datos con manejo automatico
- get_video_repo: Proporciona repositorio de videos
- get_transcription_repo: Proporciona repositorio de transcripciones
- get_summary_repo: Proporciona repositorio de resumenes
- get_source_repo: Proporciona repositorio de fuentes
- get_video_processing_service: Proporciona servicio de procesamiento
- get_downloader_service: Proporciona servicio de descarga
- get_transcription_service: Proporciona servicio de transcripcion
- get_summarization_service: Proporciona servicio de resumen

Uso en endpoints:
    @router.get("/videos/{video_id}")
    def get_video(
        video_id: UUID,
        db: Session = Depends(get_db),
        video_repo: VideoRepository = Depends(get_video_repo)
    ):
        video = video_repo.get_by_id(video_id)
        ...
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import SessionLocal
from src.repositories.source_repository import SourceRepository
from src.repositories.summary_repository import SummaryRepository
from src.repositories.transcription_repository import TranscriptionRepository
from src.repositories.video_repository import VideoRepository
from src.services.downloader_service import DownloaderService
from src.services.summarization_service import SummarizationService
from src.services.transcription_service import TranscriptionService
from src.services.video_processing_service import VideoProcessingService


# ==================== DATABASE SESSION ====================


def get_db() -> Generator[Session, None, None]:
    """
    Dependencia de FastAPI que proporciona sesion de base de datos.

    Esta dependencia:
    1. Crea una sesion de SQLAlchemy
    2. La yielda al endpoint (inyeccion)
    3. Cierra la sesion al finalizar el request (cleanup automatico)

    Yields:
        Session: Sesion de SQLAlchemy para realizar queries.

    Example:
        >>> @router.get("/videos")
        ... def list_videos(db: Session = Depends(get_db)):
        ...     videos = db.query(Video).all()
        ...     return videos
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Type alias para sesion de BD
DBSession = Annotated[Session, Depends(get_db)]


# ==================== REPOSITORIES ====================


def get_video_repo(db: DBSession) -> VideoRepository:
    """
    Dependencia que proporciona VideoRepository.

    Args:
        db: Sesion de BD (inyectada automaticamente).

    Returns:
        VideoRepository: Repositorio de videos configurado.

    Example:
        >>> @router.get("/videos/{video_id}")
        ... def get_video(
        ...     video_id: UUID,
        ...     video_repo: VideoRepository = Depends(get_video_repo)
        ... ):
        ...     return video_repo.get_by_id(video_id)
    """
    return VideoRepository(db)


def get_transcription_repo(db: DBSession) -> TranscriptionRepository:
    """
    Dependencia que proporciona TranscriptionRepository.

    Args:
        db: Sesion de BD (inyectada automaticamente).

    Returns:
        TranscriptionRepository: Repositorio de transcripciones configurado.
    """
    return TranscriptionRepository(db)


def get_summary_repo(db: DBSession) -> SummaryRepository:
    """
    Dependencia que proporciona SummaryRepository.

    Args:
        db: Sesion de BD (inyectada automaticamente).

    Returns:
        SummaryRepository: Repositorio de resumenes configurado.
    """
    return SummaryRepository(db)


def get_source_repo(db: DBSession) -> SourceRepository:
    """
    Dependencia que proporciona SourceRepository.

    Args:
        db: Sesion de BD (inyectada automaticamente).

    Returns:
        SourceRepository: Repositorio de fuentes configurado.
    """
    return SourceRepository(db)


# Type aliases para repositorios
VideoRepo = Annotated[VideoRepository, Depends(get_video_repo)]
TranscriptionRepo = Annotated[TranscriptionRepository, Depends(get_transcription_repo)]
SummaryRepo = Annotated[SummaryRepository, Depends(get_summary_repo)]
SourceRepo = Annotated[SourceRepository, Depends(get_source_repo)]


# ==================== SERVICES ====================


def get_video_processing_service() -> VideoProcessingService:
    """
    Dependencia que proporciona VideoProcessingService.

    Returns:
        VideoProcessingService: Servicio de procesamiento de videos.

    Example:
        >>> @router.post("/videos/{video_id}/process")
        ... async def process_video(
        ...     video_id: UUID,
        ...     db: DBSession,
        ...     service: VideoProcessingService = Depends(get_video_processing_service)
        ... ):
        ...     return await service.process_video(db, video_id)
    """
    return VideoProcessingService()


def get_downloader_service() -> DownloaderService:
    """
    Dependencia que proporciona DownloaderService.

    Returns:
        DownloaderService: Servicio de descarga de videos.
    """
    return DownloaderService()


def get_transcription_service() -> TranscriptionService:
    """
    Dependencia que proporciona TranscriptionService.

    Returns:
        TranscriptionService: Servicio de transcripcion.
    """
    return TranscriptionService()


def get_summarization_service() -> SummarizationService:
    """
    Dependencia que proporciona SummarizationService.

    Returns:
        SummarizationService: Servicio de generacion de resumenes.
    """
    return SummarizationService()


# Type aliases para servicios
VideoProcessingServiceDep = Annotated[
    VideoProcessingService, Depends(get_video_processing_service)
]
DownloaderServiceDep = Annotated[DownloaderService, Depends(get_downloader_service)]
TranscriptionServiceDep = Annotated[
    TranscriptionService, Depends(get_transcription_service)
]
SummarizationServiceDep = Annotated[
    SummarizationService, Depends(get_summarization_service)
]
