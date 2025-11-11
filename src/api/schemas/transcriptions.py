"""
Schemas de Pydantic para el dominio de Transcripciones.

Define schemas de request/response para endpoints de transcripciones:
- TranscriptionResponse: Respuesta completa con texto
- TranscriptionListResponse: Lista paginada de transcripciones
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.api.schemas.common import PaginatedResponse


class TranscriptionResponse(BaseModel):
    """
    Respuesta completa de transcripcion.

    Incluye el texto completo de la transcripcion.

    Example:
        >>> transcription = Transcription(...)
        >>> response = TranscriptionResponse.model_validate(transcription)
    """

    id: UUID = Field(..., description="UUID de la transcripcion")
    video_id: UUID = Field(..., description="UUID del video asociado")
    text: str = Field(..., description="Texto completo de la transcripcion")
    language: str = Field(..., description="Idioma detectado (ISO 639-1)")
    duration_seconds: float = Field(..., description="Duracion del audio transcrito")
    word_count: int = Field(..., description="Numero de palabras")
    model_version: str = Field(..., description="Version del modelo Whisper usado")
    metadata: dict = Field(default_factory=dict, description="Metadata adicional")
    created_at: datetime = Field(..., description="Fecha de creacion")
    updated_at: datetime = Field(..., description="Fecha de ultima actualizacion")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "abcd1234-5678-90ef-ghij-klmnopqrstuv",
                "video_id": "123e4567-e89b-12d3-a456-426614174000",
                "text": "This is the full transcription text of the video...",
                "language": "en",
                "duration_seconds": 212.5,
                "word_count": 780,
                "model_version": "whisper-large-v3",
                "metadata": {"segments": 45, "avg_confidence": 0.92},
                "created_at": "2025-01-15T10:35:00Z",
                "updated_at": "2025-01-15T10:35:00Z",
            }
        }


class TranscriptionListResponse(PaginatedResponse[TranscriptionResponse]):
    """
    Respuesta paginada de lista de transcripciones.

    Usa cursor-based pagination.

    Example:
        >>> response = TranscriptionListResponse(
        ...     data=[transcription1, transcription2],
        ...     cursor=CursorInfo(has_next=True, next_cursor=transcription2.id, count=2)
        ... )
    """

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "id": "abcd1234-5678-90ef-ghij-klmnopqrstuv",
                        "video_id": "123e4567-e89b-12d3-a456-426614174000",
                        "text": "This is the full transcription...",
                        "language": "en",
                        "duration_seconds": 212.5,
                        "word_count": 780,
                        "model_version": "whisper-large-v3",
                        "metadata": {},
                        "created_at": "2025-01-15T10:35:00Z",
                        "updated_at": "2025-01-15T10:35:00Z",
                    }
                ],
                "cursor": {
                    "has_next": False,
                    "next_cursor": None,
                    "count": 1,
                },
            }
        }
