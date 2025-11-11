"""
Repository para el modelo Video.

Extiende BaseRepository con métodos específicos para filtrar
videos por estado (enum VideoStatus) y por source.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from src.models import Video, VideoStatus
from src.repositories.base_repository import BaseRepository


class VideoRepository(BaseRepository[Video]):
    """
    Repository específico para el modelo Video.

    Hereda operaciones CRUD de BaseRepository y añade:
    - Filtrado por estado (pending, downloading, completed, failed)
    - Filtrado por source_id (videos de un canal específico)
    - Queries combinadas (source + estado)
    - Búsqueda por youtube_id (para evitar duplicados)
    """

    def __init__(self, session: Session):
        """
        Inicializa el repository con una sesión de SQLAlchemy.

        Args:
            session: Sesión activa de SQLAlchemy
        """
        super().__init__(session, Video)

    def get_by_status(self, status: VideoStatus) -> list[Video]:
        """
        Obtiene videos filtrados por estado.

        Útil para workers que procesan videos en estados específicos.

        Args:
            status: Estado a filtrar (VideoStatus enum)

        Returns:
            Lista de videos en ese estado

        Example:
            pending_videos = repo.get_by_status(VideoStatus.PENDING)
            for video in pending_videos:
                process_video_task.delay(video.id)
        """
        return self.session.query(Video).filter(Video.status == status).all()

    def get_by_source(self, source_id: UUID, limit: int = 100, offset: int = 0) -> list[Video]:
        """
        Obtiene videos de una fuente específica con paginación.

        Args:
            source_id: UUID de la fuente
            limit: Máximo de resultados (default 100)
            offset: Número de resultados a saltar

        Returns:
            Lista de videos de esa fuente, ordenados por fecha de publicación

        Example:
            videos = repo.get_by_source(source_id, limit=20, offset=0)
        """
        return (
            self.session.query(Video)
            .filter(Video.source_id == source_id)
            .order_by(Video.published_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_by_source_and_status(self, source_id: UUID, status: VideoStatus) -> list[Video]:
        """
        Obtiene videos de una fuente en un estado específico.

        Útil para queries como "videos pendientes del canal X".

        Args:
            source_id: UUID de la fuente
            status: Estado a filtrar

        Returns:
            Lista de videos que cumplen ambas condiciones

        Example:
            failed_videos = repo.get_by_source_and_status(
                source_id,
                VideoStatus.FAILED
            )
        """
        return (
            self.session.query(Video)
            .filter(Video.source_id == source_id, Video.status == status)
            .all()
        )

    def get_by_youtube_id(self, youtube_id: str) -> Video | None:
        """
        Busca un video por su ID de YouTube.

        Útil para evitar duplicados al scrapear canales.

        Args:
            youtube_id: ID único de YouTube (ej: "dQw4w9WgXcQ")

        Returns:
            Video si existe, None si no existe

        Example:
            existing = repo.get_by_youtube_id("dQw4w9WgXcQ")
            if existing:
                print("Video ya procesado, skip")
        """
        return self.session.query(Video).filter(Video.youtube_id == youtube_id).first()

    def exists_by_youtube_id(self, youtube_id: str) -> bool:
        """
        Verifica si existe un video con ese ID de YouTube.

        Más eficiente que get_by_youtube_id() cuando solo necesitas
        validar existencia.

        Args:
            youtube_id: ID de YouTube a verificar

        Returns:
            True si existe, False si no

        Example:
            if not repo.exists_by_youtube_id(youtube_id):
                video = Video(youtube_id=youtube_id, ...)
                repo.create(video)
        """
        return (
            self.session.query(Video.id).filter(Video.youtube_id == youtube_id).first() is not None
        )
