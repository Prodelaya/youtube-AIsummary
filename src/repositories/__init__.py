"""
Paquete de repositories para acceso a datos.

Exporta todas las excepciones y repositories para facilitar imports.
"""

from src.repositories.base_repository import BaseRepository
from src.repositories.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    RepositoryError,
)
from src.repositories.source_repository import SourceRepository
from src.repositories.summary_repository import SummaryRepository
from src.repositories.telegram_user_repository import TelegramUserRepository
from src.repositories.transcription_repository import TranscriptionRepository
from src.repositories.video_repository import VideoRepository

__all__ = [
    # Base
    "BaseRepository",
    # Repositories
    "SourceRepository",
    "VideoRepository",
    "TranscriptionRepository",
    "SummaryRepository",
    "TelegramUserRepository",
    # Excepciones
    "RepositoryError",
    "NotFoundError",
    "AlreadyExistsError",
]
