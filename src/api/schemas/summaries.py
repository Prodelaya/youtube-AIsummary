"""
Schemas de Pydantic para el dominio de Resumenes (Summaries).

Define schemas de request/response para endpoints de summaries:
- SummaryResponse: Respuesta completa con texto
- SummaryListResponse: Lista paginada de resumenes
- SummarySearchRequest: Request para busqueda full-text
- SummarySearchResponse: Respuesta de busqueda con relevancia
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.api.schemas.common import PaginatedResponse


class SummaryResponse(BaseModel):
    """
    Respuesta completa de resumen.

    Incluye el texto completo del resumen generado.

    Example:
        >>> summary = Summary(...)
        >>> response = SummaryResponse.model_validate(summary)
    """

    id: UUID = Field(..., description="UUID del resumen")
    video_id: UUID = Field(..., description="UUID del video asociado")
    title: str = Field(..., description="Titulo generado para el video")
    summary_text: str = Field(..., description="Texto completo del resumen")
    summary_type: str = Field(..., description="Tipo de resumen (comprehensive/brief)")
    key_points: list[str] = Field(..., description="Lista de puntos clave")
    topics: list[str] = Field(..., description="Temas principales identificados")
    word_count: int = Field(..., description="Numero de palabras del resumen")
    model_version: str = Field(..., description="Version del modelo usado (DeepSeek)")
    metadata: dict = Field(default_factory=dict, description="Metadata adicional")
    created_at: datetime = Field(..., description="Fecha de creacion")
    updated_at: datetime = Field(..., description="Fecha de ultima actualizacion")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "xyz98765-4321-abcd-efgh-ijklmnopqrst",
                "video_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Rick Astley's Iconic 80s Hit",
                "summary_text": "This video features Rick Astley's 1987 hit song...",
                "summary_type": "comprehensive",
                "key_points": [
                    "Classic 1980s pop song",
                    "Became internet meme phenomenon",
                    "Over 1 billion views on YouTube",
                ],
                "topics": ["music", "pop culture", "internet memes"],
                "word_count": 245,
                "model_version": "deepseek-chat",
                "metadata": {"generation_time_seconds": 3.2},
                "created_at": "2025-01-15T10:40:00Z",
                "updated_at": "2025-01-15T10:40:00Z",
            }
        }


class SummaryListResponse(PaginatedResponse[SummaryResponse]):
    """
    Respuesta paginada de lista de resumenes.

    Usa cursor-based pagination.

    Example:
        >>> response = SummaryListResponse(
        ...     data=[summary1, summary2],
        ...     cursor=CursorInfo(has_next=True, next_cursor=summary2.id, count=2)
        ... )
    """

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "id": "xyz98765-4321-abcd-efgh-ijklmnopqrst",
                        "video_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Rick Astley's Iconic 80s Hit",
                        "summary_text": "This video features Rick Astley's...",
                        "summary_type": "comprehensive",
                        "key_points": ["Classic 1980s pop song"],
                        "topics": ["music"],
                        "word_count": 245,
                        "model_version": "deepseek-chat",
                        "metadata": {},
                        "created_at": "2025-01-15T10:40:00Z",
                        "updated_at": "2025-01-15T10:40:00Z",
                    }
                ],
                "cursor": {
                    "has_next": False,
                    "next_cursor": None,
                    "count": 1,
                },
            }
        }


class SummarySearchRequest(BaseModel):
    """
    Request para busqueda full-text en resumenes.

    Usado en POST /summaries/search para buscar por palabras clave.

    Example:
        >>> request = SummarySearchRequest(
        ...     query="artificial intelligence machine learning",
        ...     limit=20
        ... )
    """

    query: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Terminos de busqueda (full-text search)",
    )
    limit: int = Field(
        20, ge=1, le=100, description="Numero maximo de resultados"
    )
    cursor: UUID | None = Field(
        None, description="Cursor para paginacion (UUID del ultimo resultado)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "artificial intelligence machine learning",
                "limit": 20,
                "cursor": None,
            }
        }


class SummarySearchResult(SummaryResponse):
    """
    Resultado de busqueda con score de relevancia.

    Hereda de SummaryResponse y añade ranking de relevancia.

    Example:
        >>> result = SummarySearchResult(
        ...     **summary.to_dict(),
        ...     relevance_score=0.85
        ... )
    """

    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score de relevancia de la busqueda (0.0 a 1.0)",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "xyz98765-4321-abcd-efgh-ijklmnopqrst",
                "video_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Introduction to Machine Learning",
                "summary_text": "This video covers fundamental concepts of ML...",
                "summary_type": "comprehensive",
                "key_points": ["Supervised vs Unsupervised Learning", "Neural Networks"],
                "topics": ["machine learning", "AI"],
                "word_count": 320,
                "model_version": "deepseek-chat",
                "metadata": {},
                "created_at": "2025-01-15T10:40:00Z",
                "updated_at": "2025-01-15T10:40:00Z",
                "relevance_score": 0.85,
            }
        }


class SummarySearchResponse(PaginatedResponse[SummarySearchResult]):
    """
    Respuesta de busqueda full-text con resultados rankeados.

    Resultados ordenados por relevancia descendente.

    Example:
        >>> response = SummarySearchResponse(
        ...     data=[result1, result2],
        ...     cursor=CursorInfo(has_next=True, next_cursor=result2.id, count=2)
        ... )
    """

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "id": "xyz98765-4321-abcd-efgh-ijklmnopqrst",
                        "video_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Introduction to Machine Learning",
                        "summary_text": "This video covers fundamental concepts...",
                        "summary_type": "comprehensive",
                        "key_points": ["Supervised Learning"],
                        "topics": ["machine learning"],
                        "word_count": 320,
                        "model_version": "deepseek-chat",
                        "metadata": {},
                        "created_at": "2025-01-15T10:40:00Z",
                        "updated_at": "2025-01-15T10:40:00Z",
                        "relevance_score": 0.85,
                    }
                ],
                "cursor": {
                    "has_next": True,
                    "next_cursor": "xyz98765-4321-abcd-efgh-ijklmnopqrst",
                    "count": 1,
                },
            }
        }
