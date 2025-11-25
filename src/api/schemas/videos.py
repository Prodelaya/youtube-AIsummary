"""
Schemas de Pydantic para el dominio de Videos.

Define los schemas de request/response para endpoints de videos:
- VideoCreateRequest: Crear un nuevo video manualmente
- VideoResponse: Respuesta basica de video
- VideoDetailResponse: Respuesta detallada con transcripcion y resumen
- VideoListResponse: Lista paginada de videos
- ProcessVideoResponse: Respuesta al encolar procesamiento
- VideoStatsResponse: Estadisticas individuales de video
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from src.api.schemas.common import CursorInfo, PaginatedResponse
from src.models.video import VideoStatus


class VideoCreateRequest(BaseModel):
    """
    Schema de request para crear un video manualmente.

    Usado en POST /videos cuando se quiere añadir un video especifico
    sin descubrimiento automatico desde la fuente.

    Example:
        >>> request = VideoCreateRequest(
        ...     source_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     youtube_id="dQw4w9WgXcQ",
        ...     title="Never Gonna Give You Up",
        ...     url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        ...     duration_seconds=212
        ... )
    """

    source_id: UUID = Field(..., description="UUID de la fuente asociada")
    youtube_id: str = Field(
        ..., min_length=11, max_length=11, description="ID del video de YouTube"
    )
    title: str = Field(..., min_length=1, max_length=500, description="Titulo del video")
    url: HttpUrl = Field(..., description="URL completa del video")
    duration_seconds: int | None = Field(None, gt=0, description="Duracion del video en segundos")
    metadata: dict[str, Any] | None = Field(
        None, description="Metadata adicional (vistas, likes, etc.)"
    )

    @field_validator("youtube_id")
    @classmethod
    def validate_youtube_id(cls, v: str) -> str:
        """Validar que el youtube_id solo contiene caracteres permitidos."""
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        if not all(c in allowed for c in v):
            raise ValueError("youtube_id contains invalid characters")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "123e4567-e89b-12d3-a456-426614174000",
                "youtube_id": "dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                "duration_seconds": 212,
                "metadata": {"view_count": 1000000, "like_count": 50000},
            }
        }


class VideoResponse(BaseModel):
    """
    Respuesta basica de video.

    Usado en listados y operaciones simples.
    No incluye relaciones (transcripcion, resumen) para optimizar payload.

    Example:
        >>> video = Video(...)
        >>> response = VideoResponse.model_validate(video.to_dict())
    """

    id: UUID = Field(..., description="UUID del video")
    source_id: UUID = Field(..., description="UUID de la fuente asociada")
    youtube_id: str = Field(..., description="ID del video de YouTube")
    title: str = Field(..., description="Titulo del video")
    url: str = Field(..., description="URL completa del video")
    duration_seconds: int | None = Field(None, description="Duracion en segundos")
    status: VideoStatus = Field(..., description="Estado del procesamiento")
    published_at: datetime | None = Field(None, description="Fecha de publicacion en YouTube")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata adicional", validation_alias="extra_metadata"
    )
    created_at: datetime = Field(..., description="Fecha de creacion en BD")
    updated_at: datetime = Field(..., description="Fecha de ultima actualizacion")
    deleted_at: datetime | None = Field(None, description="Fecha de soft delete (None = activo)")

    class Config:
        from_attributes = True  # Permite crear desde ORM models
        populate_by_name = True  # Allow both 'metadata' and 'extra_metadata'
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "source_id": "987fcdeb-51a2-43f7-9876-543210987654",
                "youtube_id": "dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                "duration_seconds": 212,
                "status": "completed",
                "published_at": "2009-10-25T06:57:33Z",
                "metadata": {"view_count": 1000000, "like_count": 50000},
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T11:45:00Z",
                "deleted_at": None,
            }
        }


class TranscriptionSummary(BaseModel):
    """
    Resumen de transcripcion para incluir en VideoDetailResponse.

    Solo incluye campos clave sin el texto completo.
    """

    id: UUID = Field(..., description="UUID de la transcripcion")
    language: str = Field(..., description="Idioma detectado (ISO 639-1)")
    duration_seconds: float = Field(..., description="Duracion del audio transcrito")
    word_count: int = Field(..., description="Numero de palabras")
    created_at: datetime = Field(..., description="Fecha de creacion")

    class Config:
        from_attributes = True


class SummarySummary(BaseModel):
    """
    Resumen de summary para incluir en VideoDetailResponse.

    Solo incluye campos clave sin el texto completo.
    """

    id: UUID = Field(..., description="UUID del resumen")
    title: str = Field(..., description="Titulo generado")
    summary_type: str = Field(..., description="Tipo de resumen generado")
    key_points: list[str] = Field(..., description="Puntos clave")
    created_at: datetime = Field(..., description="Fecha de creacion")

    class Config:
        from_attributes = True


class VideoDetailResponse(VideoResponse):
    """
    Respuesta detallada de video con transcripcion y resumen.

    Hereda de VideoResponse y añade relaciones.
    Usado en GET /videos/{id} para obtener todos los detalles.

    Example:
        >>> response = VideoDetailResponse(
        ...     **video.to_dict(),
        ...     transcription=TranscriptionSummary(...),
        ...     summary=SummarySummary(...)
        ... )
    """

    transcription: TranscriptionSummary | None = Field(
        None, description="Transcripcion asociada (None si no existe)"
    )
    summary: SummarySummary | None = Field(None, description="Resumen asociado (None si no existe)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "source_id": "987fcdeb-51a2-43f7-9876-543210987654",
                "youtube_id": "dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                "duration_seconds": 212,
                "status": "completed",
                "published_at": "2009-10-25T06:57:33Z",
                "metadata": {"view_count": 1000000},
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T11:45:00Z",
                "deleted_at": None,
                "transcription": {
                    "id": "abcd1234-5678-90ef-ghij-klmnopqrstuv",
                    "language": "en",
                    "duration_seconds": 212.5,
                    "word_count": 780,
                    "created_at": "2025-01-15T10:35:00Z",
                },
                "summary": {
                    "id": "xyz98765-4321-abcd-efgh-ijklmnopqrst",
                    "title": "Rick Astley's Iconic 80s Hit",
                    "summary_type": "comprehensive",
                    "key_points": [
                        "Classic 1980s pop song",
                        "Became internet meme phenomenon",
                        "Over 1 billion views on YouTube",
                    ],
                    "created_at": "2025-01-15T10:40:00Z",
                },
            }
        }


class VideoListResponse(PaginatedResponse[VideoResponse]):
    """
    Respuesta paginada de lista de videos.

    Usa cursor-based pagination para eficiencia en listados grandes.

    Example:
        >>> response = VideoListResponse(
        ...     data=[video1, video2, video3],
        ...     cursor=CursorInfo(has_next=True, next_cursor=video3.id, count=3)
        ... )
    """

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "source_id": "987fcdeb-51a2-43f7-9876-543210987654",
                        "youtube_id": "dQw4w9WgXcQ",
                        "title": "Never Gonna Give You Up",
                        "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                        "duration_seconds": 212,
                        "status": "completed",
                        "published_at": "2009-10-25T06:57:33Z",
                        "metadata": {},
                        "created_at": "2025-01-15T10:30:00Z",
                        "updated_at": "2025-01-15T11:45:00Z",
                        "deleted_at": None,
                    }
                ],
                "cursor": {
                    "has_next": True,
                    "next_cursor": "123e4567-e89b-12d3-a456-426614174000",
                    "count": 1,
                },
            }
        }


class ProcessVideoResponse(BaseModel):
    """
    Respuesta al encolar un video para procesamiento.

    Usado en POST /videos/{id}/process y POST /videos/{id}/retry.

    Example:
        >>> response = ProcessVideoResponse(
        ...     task_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        ...     video_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     message="Video enqueued for processing"
        ... )
    """

    task_id: str = Field(..., description="ID de la tarea Celery")
    video_id: UUID = Field(..., description="UUID del video")
    message: str = Field(..., description="Mensaje descriptivo")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "video_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Video enqueued for processing",
            }
        }


class VideoStatsResponse(BaseModel):
    """
    Estadisticas individuales de un video.

    Usado en GET /videos/{id}/stats para obtener metricas especificas.

    Example:
        >>> stats = VideoStatsResponse(
        ...     video_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     duration_seconds=212,
        ...     transcription_word_count=780,
        ...     summary_key_points_count=5,
        ...     processing_time_seconds=245.7
        ... )
    """

    video_id: UUID = Field(..., description="UUID del video")
    duration_seconds: int | None = Field(None, description="Duracion del video")
    transcription_word_count: int | None = Field(None, description="Palabras en transcripcion")
    summary_key_points_count: int | None = Field(
        None, description="Numero de puntos clave en resumen"
    )
    processing_time_seconds: float | None = Field(
        None, description="Tiempo total de procesamiento (download + transcribe + summarize)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "123e4567-e89b-12d3-a456-426614174000",
                "duration_seconds": 212,
                "transcription_word_count": 780,
                "summary_key_points_count": 5,
                "processing_time_seconds": 245.7,
            }
        }
