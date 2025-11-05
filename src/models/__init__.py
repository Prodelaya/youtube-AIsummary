"""
Paquete de modelos SQLAlchemy.

Este módulo exporta todos los modelos de base de datos para facilitar
su importación en otras partes del código.
También expone la clase Base para las migraciones de Alembic.

Uso:
    from src.models import Base, Source, Video, Transcription, Summary
    from src.models import VideoStatus  # Enum
"""

from src.models.base import Base, TimestampedUUIDBase, TimestampMixin, UUIDMixin
from src.models.source import Source
from src.models.summary import Summary
from src.models.transcription import Transcription
from src.models.video import Video, VideoStatus

# Exportar todos los modelos y Base para uso en otros módulos
__all__ = [
    # Clases base
    "Base",
    "TimestampedUUIDBase",
    "TimestampMixin",
    "UUIDMixin",
    # Modelos
    "Source",
    "Video",
    "Transcription",
    "Summary",
    # Enums
    "VideoStatus",
]
