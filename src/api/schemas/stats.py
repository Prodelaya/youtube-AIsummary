"""
Schemas de Pydantic para el dominio de Estadisticas.

Define schemas para endpoints de estadisticas globales:
- GlobalStatsResponse: Estadisticas generales del sistema
- SourceStatsResponse: Estadisticas agrupadas por fuente
"""

from uuid import UUID

from pydantic import BaseModel, Field


class SourceStats(BaseModel):
    """
    Estadisticas de una fuente individual.

    Usado dentro de GlobalStatsResponse para desglose por fuente.
    """

    source_id: UUID = Field(..., description="UUID de la fuente")
    source_name: str = Field(..., description="Nombre de la fuente")
    total_videos: int = Field(..., ge=0, description="Total de videos de esta fuente")
    completed_videos: int = Field(
        ..., ge=0, description="Videos completamente procesados"
    )
    failed_videos: int = Field(..., ge=0, description="Videos con procesamiento fallido")
    pending_videos: int = Field(
        ..., ge=0, description="Videos pendientes de procesar"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "987fcdeb-51a2-43f7-9876-543210987654",
                "source_name": "Lex Fridman Podcast",
                "total_videos": 150,
                "completed_videos": 142,
                "failed_videos": 3,
                "pending_videos": 5,
            }
        }


class GlobalStatsResponse(BaseModel):
    """
    Estadisticas globales del sistema.

    Usado en GET /stats para obtener metricas generales.

    Example:
        >>> stats = GlobalStatsResponse(
        ...     total_videos=500,
        ...     completed_videos=450,
        ...     failed_videos=10,
        ...     pending_videos=40,
        ...     total_transcriptions=450,
        ...     total_summaries=450,
        ...     sources=[source_stats1, source_stats2]
        ... )
    """

    total_videos: int = Field(..., ge=0, description="Total de videos en el sistema")
    completed_videos: int = Field(
        ..., ge=0, description="Videos completamente procesados"
    )
    failed_videos: int = Field(..., ge=0, description="Videos con errores")
    pending_videos: int = Field(..., ge=0, description="Videos pendientes")
    total_transcriptions: int = Field(
        ..., ge=0, description="Total de transcripciones generadas"
    )
    total_summaries: int = Field(..., ge=0, description="Total de resumenes generados")
    sources: list[SourceStats] = Field(
        ..., description="Desglose de estadisticas por fuente"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_videos": 500,
                "completed_videos": 450,
                "failed_videos": 10,
                "pending_videos": 40,
                "total_transcriptions": 450,
                "total_summaries": 450,
                "sources": [
                    {
                        "source_id": "987fcdeb-51a2-43f7-9876-543210987654",
                        "source_name": "Lex Fridman Podcast",
                        "total_videos": 150,
                        "completed_videos": 142,
                        "failed_videos": 3,
                        "pending_videos": 5,
                    },
                    {
                        "source_id": "123e4567-e89b-12d3-a456-426614174000",
                        "source_name": "Two Minute Papers",
                        "total_videos": 350,
                        "completed_videos": 308,
                        "failed_videos": 7,
                        "pending_videos": 35,
                    },
                ],
            }
        }


class SourceStatsResponse(BaseModel):
    """
    Estadisticas detalladas de una fuente especifica.

    Usado en GET /stats/sources/{source_id} para metricas de una fuente.

    Example:
        >>> stats = SourceStatsResponse(
        ...     source_id=UUID("987fcdeb-51a2-43f7-9876-543210987654"),
        ...     source_name="Lex Fridman Podcast",
        ...     total_videos=150,
        ...     completed_videos=142,
        ...     failed_videos=3,
        ...     pending_videos=5,
        ...     avg_processing_time_seconds=245.3,
        ...     total_transcription_words=125000
        ... )
    """

    source_id: UUID = Field(..., description="UUID de la fuente")
    source_name: str = Field(..., description="Nombre de la fuente")
    total_videos: int = Field(..., ge=0, description="Total de videos")
    completed_videos: int = Field(..., ge=0, description="Videos completados")
    failed_videos: int = Field(..., ge=0, description="Videos fallidos")
    pending_videos: int = Field(..., ge=0, description="Videos pendientes")
    avg_processing_time_seconds: float | None = Field(
        None,
        ge=0.0,
        description="Tiempo promedio de procesamiento por video (segundos)",
    )
    total_transcription_words: int | None = Field(
        None, ge=0, description="Total de palabras transcritas de esta fuente"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "987fcdeb-51a2-43f7-9876-543210987654",
                "source_name": "Lex Fridman Podcast",
                "total_videos": 150,
                "completed_videos": 142,
                "failed_videos": 3,
                "pending_videos": 5,
                "avg_processing_time_seconds": 245.3,
                "total_transcription_words": 125000,
            }
        }
