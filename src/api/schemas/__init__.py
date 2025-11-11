"""
Schemas de Pydantic para la API REST.

Este modulo exporta todos los schemas de request/response organizados por dominio.

Dominios:
- common: Schemas reutilizables (paginacion, mensajes, errores)
- videos: Schemas de videos
- transcriptions: Schemas de transcripciones
- summaries: Schemas de resumenes
- stats: Schemas de estadisticas
"""

# Common schemas
from src.api.schemas.common import CursorInfo, MessageResponse, PaginatedResponse

# Error schemas
from src.api.schemas.errors import (
    ErrorDetail,
    ErrorResponse,
    ValidationErrorResponse,
)

# Video schemas
from src.api.schemas.videos import (
    ProcessVideoResponse,
    SummarySummary,
    TranscriptionSummary,
    VideoCreateRequest,
    VideoDetailResponse,
    VideoListResponse,
    VideoResponse,
    VideoStatsResponse,
)

# Transcription schemas
from src.api.schemas.transcriptions import (
    TranscriptionListResponse,
    TranscriptionResponse,
)

# Summary schemas
from src.api.schemas.summaries import (
    SummaryListResponse,
    SummaryResponse,
    SummarySearchRequest,
    SummarySearchResponse,
    SummarySearchResult,
)

# Stats schemas
from src.api.schemas.stats import (
    GlobalStatsResponse,
    SourceStats,
    SourceStatsResponse,
)

__all__ = [
    # Common
    "CursorInfo",
    "MessageResponse",
    "PaginatedResponse",
    # Errors
    "ErrorDetail",
    "ErrorResponse",
    "ValidationErrorResponse",
    # Videos
    "ProcessVideoResponse",
    "SummarySummary",
    "TranscriptionSummary",
    "VideoCreateRequest",
    "VideoDetailResponse",
    "VideoListResponse",
    "VideoResponse",
    "VideoStatsResponse",
    # Transcriptions
    "TranscriptionListResponse",
    "TranscriptionResponse",
    # Summaries
    "SummaryListResponse",
    "SummaryResponse",
    "SummarySearchRequest",
    "SummarySearchResponse",
    "SummarySearchResult",
    # Stats
    "GlobalStatsResponse",
    "SourceStats",
    "SourceStatsResponse",
]
