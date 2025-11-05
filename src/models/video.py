"""
Modelo Video - Representa videos individuales de las fuentes.

Los videos se descubren de las fuentes (canales) y pasan por un pipeline:
pending → downloading → downloaded → transcribing → transcribed →
summarizing → completed
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import TimestampedUUIDBase

# Import solo para type checking (no causa import circular)
if TYPE_CHECKING:
    from src.models.source import Source
    from src.models.transcription import Transcription


class VideoStatus(str, enum.Enum):
    """
    Enum de estado de procesamiento del video.

    El video pasa por estos estados en orden durante el procesamiento.
    El estado failed puede ocurrir en cualquier punto si hay errores.
    """

    PENDING = "pending"  # Descubierto pero aún no descargado
    DOWNLOADING = "downloading"  # Descargando audio actualmente
    DOWNLOADED = "downloaded"  # Audio descargado, listo para transcripción
    TRANSCRIBING = "transcribing"  # Whisper está transcribiendo
    TRANSCRIBED = "transcribed"  # Transcripción completa, listo para resumen
    SUMMARIZING = "summarizing"  # ApyHub está generando resumen
    COMPLETED = "completed"  # Completamente procesado (transcrito + resumido)
    FAILED = "failed"  # El procesamiento falló en algún paso


class Video(TimestampedUUIDBase):
    """
    Video individual de una fuente.

    Representa un video que será descargado, transcrito y resumido.
    Rastrea el estado del procesamiento y almacena metadata de YouTube/RSS.

    Atributos:
        id: Clave primaria UUID (de TimestampedUUIDBase)
        source_id: Clave foránea al modelo Source
        youtube_id: ID del video de YouTube (identificador único)
        title: Título del video
        url: URL completa del video
        duration_seconds: Duración del video en segundos
        status: Estado actual del procesamiento (enum)
        published_at: Cuándo se publicó el video en YouTube
        metadata: Campo JSON flexible para datos extra (vistas, likes, etc.)
        created_at: Timestamp de cuándo se añadió (de TimestampedUUIDBase)
        updated_at: Timestamp última modificación (de TimestampedUUIDBase)
        source: Relación al modelo Source (muchos-a-uno)

    Ejemplos:
        >>> video = Video(
        ...     source_id=source.id,
        ...     youtube_id="dQw4w9WgXcQ",
        ...     title="Never Gonna Give You Up",
        ...     url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        ...     duration_seconds=212,
        ...     status=VideoStatus.PENDING,
        ...     metadata={"view_count": 1000000, "like_count": 50000}
        ... )
    """

    __tablename__ = "videos"

    # ==================== COLUMNAS ====================

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        comment="Clave foránea a la tabla sources",
    )

    youtube_id: Mapped[str] = mapped_column(
        String(20),  # IDs de YouTube son 11 chars, usamos 20 por seguridad
        nullable=False,
        unique=True,  # Prevenir videos duplicados
        comment="ID del video de YouTube (ej: 'dQw4w9WgXcQ')",
    )

    title: Mapped[str] = mapped_column(
        String(500),  # Títulos de YouTube pueden ser largos
        nullable=False,
        comment="Título del video desde YouTube",
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="URL completa del video de YouTube",
    )

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Duración del video en segundos (para estimar tiempo)",
    )

    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, name="video_status", native_enum=False),
        nullable=False,
        default=VideoStatus.PENDING,
        comment="Estado actual del procesamiento en el pipeline",
    )

    published_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Cuándo se publicó el video en YouTube",
    )

    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # Nombre real de la columna en la tabla SQL
        JSONB,
        nullable=True,
        default=dict,
        comment="Metadatos adicionales (vistas, likes, thumbnail, etc.)",
    )

    # ==================== RELACIONES ====================

    # Muchos-a-uno: Muchos videos pertenecen a una fuente
    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="videos",
        lazy="joined",  # Carga eager de source al consultar video
    )

    # Uno-a-uno: Un video tiene una transcripción
    transcription: Mapped["Transcription"] = relationship(
        "Transcription",
        back_populates="video",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,  # Forzar relación 1:1 (no lista)
    )

    # ==================== ÍNDICES ====================
    __table_args__ = (
        Index("ix_videos_source_id", "source_id"),  # Filtrado rápido por fuente
        Index("ix_videos_status", "status"),  # Filtrado rápido por estado
        Index("ix_videos_youtube_id", "youtube_id"),  # Búsqueda rápida por ID
        Index("ix_videos_published_at", "published_at"),  # Orden por fecha
        # Índice compuesto para query común: "videos pendientes de X fuente"
        Index("ix_videos_source_status", "source_id", "status"),
    )

    # ==================== MÉTODOS ====================

    def __repr__(self) -> str:
        """Representación en string para debugging."""
        return (
            f"<Video(id={self.id}, youtube_id='{self.youtube_id}', "
            f"title='{self.title[:50]}...', status={self.status.value})>"
        )

    def to_dict(self) -> dict:
        """
        Convertir modelo a diccionario.

        Útil para serialización JSON en respuestas de API.

        Returns:
            dict: Representación en diccionario del video.
        """
        return {
            "id": str(self.id),
            "source_id": str(self.source_id),
            "youtube_id": self.youtube_id,
            "title": self.title,
            "url": self.url,
            "duration_seconds": self.duration_seconds,
            "status": self.status.value,
            "published_at": (self.published_at.isoformat() if self.published_at else None),
            "metadata": self.extra_metadata or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def is_processed(self) -> bool:
        """Verificar si el video ha completado el procesamiento."""
        return self.status == VideoStatus.COMPLETED

    @property
    def has_failed(self) -> bool:
        """Verificar si el procesamiento del video falló."""
        return self.status == VideoStatus.FAILED

    @property
    def is_processing(self) -> bool:
        """Verificar si el video está siendo procesado actualmente."""
        return self.status in {
            VideoStatus.DOWNLOADING,
            VideoStatus.TRANSCRIBING,
            VideoStatus.SUMMARIZING,
        }
