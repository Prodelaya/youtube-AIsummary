"""
Modelo Transcription - Representa transcripciones de audio generadas por Whisper.

Las transcripciones se generan a partir del audio descargado de videos.
Contienen el texto completo, metadata técnica y opcionalmente segmentos
con timestamps para búsqueda temporal futura.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import TimestampedUUIDBase

# Import solo para type checking (no causa import circular)
if TYPE_CHECKING:
    from src.models.summary import Summary
    from src.models.video import Video


class Transcription(TimestampedUUIDBase):
    """
    Transcripción de audio generada por Whisper.

    Almacena el texto transcrito del audio de un video, junto con metadata
    técnica sobre el proceso de transcripción (modelo usado, idioma detectado,
    duración). Opcionalmente incluye segmentos con timestamps.

    Atributos:
        id: Clave primaria UUID (de TimestampedUUIDBase)
        video_id: Clave foránea al modelo Video (relación 1:1)
        text: Texto completo de la transcripción
        language: Código ISO 639-1 del idioma detectado (ej: 'es', 'en')
        model_used: Nombre del modelo Whisper usado ('whisper-base', 'whisper-small')
        duration_seconds: Duración del audio transcrito en segundos
        segments: Segmentos con timestamps en formato JSON (opcional)
        confidence_score: Puntuación de confianza promedio (0.0-1.0)
        created_at: Timestamp de creación (de TimestampedUUIDBase)
        updated_at: Timestamp última modificación (de TimestampedUUIDBase)
        video: Relación al modelo Video (uno-a-uno)
        summary: Relación al modelo Summary (uno-a-uno)

    Ejemplos:
        >>> transcription = Transcription(
        ...     video_id=video.id,
        ...     text="Hola, bienvenidos a este tutorial sobre FastAPI...",
        ...     language="es",
        ...     model_used="whisper-base",
        ...     duration_seconds=212,
        ...     confidence_score=0.89
        ... )
    """

    __tablename__ = "transcriptions"

    # ==================== COLUMNAS ====================

    video_id: Mapped[UUID] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Relación 1:1 con Video
        comment="Clave foránea al video transcrito",
    )

    text: Mapped[str] = mapped_column(
        Text,  # Sin límite de longitud
        nullable=False,
        comment="Texto completo de la transcripción",
    )

    language: Mapped[str] = mapped_column(
        String(10),  # Códigos ISO son cortos (ej: 'es', 'en-US')
        nullable=False,
        default="es",
        comment="Código ISO 639-1 del idioma detectado",
    )

    model_used: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="whisper-base",
        comment="Modelo Whisper usado ('whisper-base', 'whisper-small', etc.)",
    )

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Duración del audio transcrito en segundos",
    )

    segments: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Segmentos con timestamps en formato JSON (opcional)",
    )

    confidence_score: Mapped[float | None] = mapped_column(
        # Usamos String + validación manual porque SQLAlchemy Float no tiene NUMERIC(precision)
        # En producción podrías usar: from sqlalchemy import Numeric -> Numeric(3, 2)
        nullable=True,
        comment="Puntuación de confianza promedio (0.0-1.0)",
    )

    # ==================== RELACIONES ====================

    # Uno-a-uno: Una transcripción pertenece a un video
    video: Mapped["Video"] = relationship(
        "Video",
        back_populates="transcription",
        lazy="joined",  # Carga eager del video al consultar transcripción
    )

    # Uno-a-uno: Una transcripción tiene un resumen
    summary: Mapped["Summary"] = relationship(
        "Summary",
        back_populates="transcription",
        cascade="all, delete-orphan",  # Si se borra transcripción, borra resumen
        lazy="selectin",
        uselist=False,  # Forzar relación 1:1 (no lista)
    )

    # ==================== ÍNDICES ====================
    __table_args__ = (
        Index("ix_transcriptions_video_id", "video_id"),
        Index("ix_transcriptions_language", "language"),
        # NOTE: Índices GIN y full-text search se crean en la migración
    )

    # ==================== MÉTODOS ====================

    def __repr__(self) -> str:
        """Representación en string para debugging."""
        return (
            f"<Transcription(id={self.id}, video_id={self.video_id}, "
            f"language='{self.language}', model='{self.model_used}', "
            f"length={len(self.text)} chars)>"
        )

    def to_dict(self) -> dict:
        """
        Convertir modelo a diccionario.

        Útil para serialización JSON en respuestas de API.

        Returns:
            dict: Representación en diccionario de la transcripción.
        """
        return {
            "id": str(self.id),
            "video_id": str(self.video_id),
            "text": self.text,
            "language": self.language,
            "model_used": self.model_used,
            "duration_seconds": self.duration_seconds,
            "segments": self.segments or {},
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def word_count(self) -> int:
        """Calcular número aproximado de palabras en la transcripción."""
        return len(self.text.split())

    @property
    def has_segments(self) -> bool:
        """Verificar si la transcripción incluye segmentos con timestamps."""
        return self.segments is not None and len(self.segments) > 0

    @property
    def is_high_confidence(self) -> bool:
        """
        Verificar si la transcripción tiene alta confianza.

        Se considera alta confianza si el score >= 0.85.
        """
        if self.confidence_score is None:
            return False
        return self.confidence_score >= 0.85
