"""
Modelo Source - Representa fuentes de contenido (canales YouTube, RSS, etc.).

Una Source es el origen de videos/contenido que será procesado por el sistema.
Ejemplos: canales de YouTube, feeds RSS de podcasts, feeds de blogs.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import TimestampedUUIDBase

# Import solo para type checking (no causa import circular)
if TYPE_CHECKING:
    from src.models.video import Video


class Source(TimestampedUUIDBase):
    """
    Fuente de contenido (canal YouTube, feed RSS, etc.).

    Atributos:
        id: Clave primaria UUID (de TimestampedUUIDBase)
        name: Nombre legible de la fuente
        url: URL de la fuente (ej: URL del canal de YouTube)
        source_type: Tipo de fuente ('youtube', 'rss', 'podcast')
        active: Si la fuente está siendo monitoreada actualmente
        metadata: Campo JSON flexible para datos extra (suscriptores, avatar, etc.)
        created_at: Timestamp de cuándo se añadió (de TimestampedUUIDBase)
        updated_at: Timestamp de última modificación (de TimestampedUUIDBase)
        videos: Relación al modelo Video (uno-a-muchos)

    Ejemplos:
        >>> source = Source(
        ...     name="DotCSV",
        ...     url="https://youtube.com/@DotCSV",
        ...     source_type="youtube",
        ...     active=True,
        ...     metadata={"subscriber_count": 500000, "language": "es"}
        ... )
    """

    __tablename__ = "sources"

    # ==================== COLUMNAS ====================

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nombre de la fuente (ej: nombre del canal)",
    )

    url: Mapped[str] = mapped_column(
        Text,  # Text en lugar de String para URLs largas
        nullable=False,
        unique=True,  # Prevenir fuentes duplicadas
        comment="URL de la fuente (canal YouTube, feed RSS, etc.)",
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="youtube",
        comment="Tipo de fuente: 'youtube', 'rss', 'podcast'",
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Si esta fuente está siendo monitoreada activamente",
    )

    metadata: Mapped[dict | None] = mapped_column(
        JSONB,  # Tipo JSONB de PostgreSQL (indexable, consultable)
        nullable=True,
        default=dict,  # Dict vacío por defecto
        comment="Metadatos adicionales (suscriptores, thumbnail, etc.)",
    )

    # ==================== RELACIONES ====================

    # Uno-a-muchos: Una fuente tiene muchos videos
    # back_populates crea relación bidireccional
    # cascade="all, delete-orphan" significa: si se borra source, borra videos
    videos: Mapped[list["Video"]] = relationship(
        "Video",
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="selectin",  # Carga eager de videos al consultar source
    )

    # ==================== ÍNDICES ====================
    # Crear índices para columnas usadas frecuentemente en WHERE
    __table_args__ = (
        Index("ix_sources_active", "active"),  # Filtrado rápido por estado
        Index("ix_sources_source_type", "source_type"),  # Filtrado por tipo
    )

    # ==================== MÉTODOS ====================

    def __repr__(self) -> str:
        """Representación en string para debugging."""
        return (
            f"<Source(id={self.id}, name='{self.name}', "
            f"type='{self.source_type}', active={self.active})>"
        )

    def to_dict(self) -> dict:
        """
        Convertir modelo a diccionario.

        Útil para serialización JSON en respuestas de API.

        Returns:
            dict: Representación en diccionario de la fuente.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "url": self.url,
            "source_type": self.source_type,
            "active": self.active,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
