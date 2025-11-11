"""
Repository para el modelo Transcription.

Extiende BaseRepository con métodos específicos para buscar
transcripciones por video_id y filtrar por idioma.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from src.models import Transcription
from src.repositories.base_repository import BaseRepository


class TranscriptionRepository(BaseRepository[Transcription]):
    """
    Repository específico para el modelo Transcription.

    Hereda operaciones CRUD de BaseRepository y añade:
    - Búsqueda por video_id (relación 1:1)
    - Filtrado por idioma
    - Validación de existencia por video_id
    """

    def __init__(self, session: Session):
        """
        Inicializa el repository con una sesión de SQLAlchemy.

        Args:
            session: Sesión activa de SQLAlchemy
        """
        super().__init__(session, Transcription)

    def get_by_video_id(self, video_id: UUID) -> Transcription | None:
        """
        Busca la transcripción de un video específico.

        Como la relación es 1:1, solo puede haber una transcripción por video.

        Args:
            video_id: UUID del video

        Returns:
            Transcription si existe, None si el video no tiene transcripción

        Example:
            transcription = repo.get_by_video_id(video_id)
            if transcription:
                # Generar resumen usando transcription.transcription
                pass
        """
        return self.session.query(Transcription).filter(Transcription.video_id == video_id).first()

    def exists_by_video_id(self, video_id: UUID) -> bool:
        """
        Verifica si un video ya tiene transcripción.

        Útil para evitar re-transcribir videos ya procesados.

        Args:
            video_id: UUID del video a verificar

        Returns:
            True si el video ya tiene transcripción, False si no

        Example:
            if not repo.exists_by_video_id(video_id):
                # Transcribir el video con Whisper
                transcribe_task.delay(video_id)
        """
        return (
            self.session.query(Transcription.id).filter(Transcription.video_id == video_id).first()
            is not None
        )

    def get_by_language(self, language: str) -> list[Transcription]:
        """
        Obtiene transcripciones filtradas por idioma.

        Útil para analytics y estadísticas.

        Args:
            language: Código de idioma (ISO 639-1: "es", "en", etc.)

        Returns:
            Lista de transcripciones en ese idioma

        Example:
            spanish_transcriptions = repo.get_by_language("es")
            print(f"Total en español: {len(spanish_transcriptions)}")
        """
        return self.session.query(Transcription).filter(Transcription.language == language).all()
