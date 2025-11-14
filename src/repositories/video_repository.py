"""
Repository para el modelo Video.

Extiende BaseRepository con métodos específicos para filtrar
videos por estado (enum VideoStatus) y por source.

Incluye invalidación automática de caché de estadísticas al crear videos.
"""

import logging
from datetime import UTC
from uuid import UUID

from sqlalchemy.orm import Session

from src.models import Video, VideoStatus
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


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

    def _invalidate_stats_cache(self, source_id: UUID) -> None:
        """
        Invalida caché de estadísticas al crear/modificar videos.

        Invalida:
        - stats:global (estadísticas globales)
        - stats:source:{source_id} (estadísticas de la fuente específica)

        Args:
            source_id: UUID de la fuente del video

        Example:
            self._invalidate_stats_cache(video.source_id)
        """
        # Import lazy para evitar importación circular
        from src.services.cache_service import cache_service

        # Invalidar caché global
        global_key = "stats:global"
        cache_service.delete(global_key)
        logger.debug(f"Invalidated cache: {global_key}")

        # Invalidar caché de la fuente específica
        source_key = f"stats:source:{source_id}"
        cache_service.delete(source_key)
        logger.debug(f"Invalidated cache: {source_key}")

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

    def list_paginated(
        self,
        limit: int = 20,
        cursor: UUID | None = None,
        status: VideoStatus | None = None,
        source_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> list[Video]:
        """
        Lista videos con paginacion cursor-based.

        Args:
            limit: Numero maximo de videos a retornar.
            cursor: UUID del ultimo video (para paginacion).
            status: Filtrar por estado (opcional).
            source_id: Filtrar por fuente (opcional).
            include_deleted: Incluir videos soft-deleted.

        Returns:
            Lista de videos ordenados por created_at DESC.

        Example:
            # Primera pagina
            videos = repo.list_paginated(limit=20)

            # Segunda pagina
            last_id = videos[-1].id
            next_videos = repo.list_paginated(limit=20, cursor=last_id)
        """

        query = self.session.query(Video)

        # Filtro de soft delete
        if not include_deleted:
            query = query.filter(Video.deleted_at.is_(None))

        # Filtro de status
        if status:
            query = query.filter(Video.status == status)

        # Filtro de source
        if source_id:
            query = query.filter(Video.source_id == source_id)

        # Paginacion cursor-based
        if cursor:
            # Obtener created_at del cursor
            cursor_video = self.session.query(Video).filter(Video.id == cursor).first()
            if cursor_video:
                query = query.filter(Video.created_at < cursor_video.created_at)

        # Ordenar y limitar
        query = query.order_by(Video.created_at.desc()).limit(limit)

        return query.all()

    def create_video(
        self,
        source_id: UUID,
        youtube_id: str,
        title: str,
        url: str,
        duration_seconds: int | None = None,
        metadata: dict | None = None,
        status: VideoStatus = VideoStatus.PENDING,
    ) -> Video:
        """
        Crea un nuevo video con parametros individuales.

        Invalida automáticamente caché de estadísticas (global y de la fuente).

        Args:
            source_id: UUID de la fuente.
            youtube_id: ID de YouTube.
            title: Titulo del video.
            url: URL completa.
            duration_seconds: Duracion en segundos (opcional).
            metadata: Metadata adicional (opcional).
            status: Estado inicial (default PENDING).

        Returns:
            Video creado y persistido.

        Example:
            video = repo.create_video(
                source_id=source.id,
                youtube_id="dQw4w9WgXcQ",
                title="Never Gonna Give You Up",
                url="https://youtube.com/watch?v=dQw4w9WgXcQ"
            )
        """
        video = Video(
            source_id=source_id,
            youtube_id=youtube_id,
            title=title,
            url=url,
            duration_seconds=duration_seconds,
            extra_metadata=metadata or {},
            status=status,
        )

        # Crear video en BD
        created_video = self.create(video)

        # Invalidar caché de estadísticas
        self._invalidate_stats_cache(source_id)

        logger.info(
            f"Video created and stats cache invalidated",
            extra={"video_id": str(created_video.id), "source_id": str(source_id)},
        )

        return created_video

    def update_video(self, video_id: UUID, **kwargs) -> Video:
        """
        Actualiza campos de un video.

        Invalida caché de estadísticas si se actualiza el campo 'status'.

        Args:
            video_id: UUID del video a actualizar.
            **kwargs: Campos a actualizar (title, duration_seconds, status, etc.).

        Returns:
            Video actualizado.

        Raises:
            ValueError: Si el video no existe.

        Example:
            video = repo.update_video(
                video_id,
                status=VideoStatus.COMPLETED
            )
        """
        video = self.get_by_id(video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Detectar si se está cambiando el estado (para invalidar caché)
        status_changed = "status" in kwargs and kwargs["status"] != video.status

        for key, value in kwargs.items():
            if hasattr(video, key):
                setattr(video, key, value)

        self.session.commit()
        self.session.refresh(video)

        # Invalidar caché si cambió el estado
        if status_changed:
            self._invalidate_stats_cache(video.source_id)
            logger.info(
                f"Video status updated and stats cache invalidated",
                extra={
                    "video_id": str(video_id),
                    "new_status": kwargs["status"].value if hasattr(kwargs["status"], "value") else str(kwargs["status"]),
                    "source_id": str(video.source_id),
                },
            )

        return video

    def soft_delete(self, video_id: UUID) -> Video:
        """
        Soft delete de un video (establece deleted_at).

        Args:
            video_id: UUID del video a eliminar.

        Returns:
            Video con deleted_at establecido.

        Raises:
            ValueError: Si el video no existe.

        Example:
            video = repo.soft_delete(video_id)
            assert video.is_deleted is True
        """
        from datetime import datetime

        video = self.get_by_id(video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        video.deleted_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(video)
        return video

    def get_skipped_videos(
        self, source_id: UUID | None = None, limit: int = 50
    ) -> list[Video]:
        """
        Obtiene videos que fueron descartados (status=SKIPPED).

        Útil para reportes y análisis de contenido no procesado.

        Args:
            source_id: Filtrar por fuente específica (opcional).
            limit: Máximo de resultados (default 50).

        Returns:
            Lista de videos con status SKIPPED, ordenados por fecha.

        Example:
            skipped = repo.get_skipped_videos(limit=10)
            for video in skipped:
                print(f"Skipped: {video.title} ({video.duration_seconds}s)")
        """
        query = self.session.query(Video).filter(Video.status == VideoStatus.SKIPPED)

        if source_id:
            query = query.filter(Video.source_id == source_id)

        return query.order_by(Video.created_at.desc()).limit(limit).all()

    def get_stats_by_status(self) -> dict[VideoStatus, int]:
        """
        Cuenta videos agrupados por status.

        Returns:
            Dict con counts por status: {PENDING: 5, COMPLETED: 20, SKIPPED: 3, ...}

        Example:
            stats = repo.get_stats_by_status()
            print(f"Videos descartados: {stats.get(VideoStatus.SKIPPED, 0)}")
        """
        from sqlalchemy import func

        result = (
            self.session.query(Video.status, func.count(Video.id))
            .group_by(Video.status)
            .all()
        )

        return {status: count for status, count in result}
