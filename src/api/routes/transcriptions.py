"""
Router de Transcriptions - Endpoints para transcripciones.

Este modulo define 3 endpoints para acceso a transcripciones:
1. GET /transcriptions              - Listar transcripciones (paginado)
2. GET /transcriptions/{id}         - Obtener detalle de transcripcion
3. GET /videos/{video_id}/transcription - Transcripcion de un video especifico

Las transcripciones son generadas por el servicio de procesamiento
y contienen el texto completo del audio transcrito por Whisper.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.dependencies import TranscriptionRepo
from src.api.schemas.common import CursorInfo
from src.api.schemas.transcriptions import (
    TranscriptionListResponse,
    TranscriptionResponse,
)

# ==================== ROUTER ====================

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


# ==================== ENDPOINTS ====================


@router.get(
    "",
    response_model=TranscriptionListResponse,
    summary="List transcriptions",
    description="List all transcriptions with cursor-based pagination.",
    responses={
        200: {
            "description": "List of transcriptions with pagination",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "video_id": "987fcdeb-51a2-43f7-9876-543210987654",
                                "text": "Welcome to this tutorial on FastAPI. Today we will cover...",
                                "language": "en",
                                "model_used": "whisper-large-v3",
                                "duration_seconds": 212.5,
                                "confidence_score": 0.95,
                                "created_at": "2025-01-15T11:30:00Z",
                            }
                        ],
                        "cursor": {
                            "has_next": True,
                            "next_cursor": "123e4567-e89b-12d3-a456-426614174000",
                            "count": 1,
                        },
                    }
                }
            },
        }
    },
)
def list_transcriptions(
    transcription_repo: TranscriptionRepo,
    limit: int = Query(20, ge=1, le=100, description="Number of transcriptions to return"),
    cursor: UUID | None = Query(None, description="Cursor for pagination (last transcription ID)"),
) -> TranscriptionListResponse:
    """
    Listar transcripciones con paginacion cursor-based.

    Args:
        transcription_repo: Repositorio de transcripciones (inyectado).
        limit: Numero de transcripciones a retornar (1-100, default 20).
        cursor: UUID de la ultima transcripcion (para paginacion).

    Returns:
        TranscriptionListResponse: Lista paginada de transcripciones.

    Example:
        GET /api/v1/transcriptions?limit=20
        GET /api/v1/transcriptions?cursor=123e4567-e89b-12d3-a456-426614174000&limit=20
    """
    transcriptions = transcription_repo.list_paginated(limit=limit, cursor=cursor)

    # Determinar si hay mas elementos
    has_next = len(transcriptions) == limit
    next_cursor = transcriptions[-1].id if has_next and transcriptions else None

    # Convertir a schemas
    transcription_responses = [TranscriptionResponse.model_validate(t) for t in transcriptions]

    return TranscriptionListResponse(
        data=transcription_responses,
        cursor=CursorInfo(
            has_next=has_next,
            next_cursor=next_cursor,
            count=len(transcription_responses),
        ),
    )


@router.get(
    "/{transcription_id}",
    response_model=TranscriptionResponse,
    summary="Get transcription details",
    description="Get full transcription text and metadata by ID.",
)
def get_transcription(
    transcription_id: UUID,
    transcription_repo: TranscriptionRepo,
) -> TranscriptionResponse:
    """
    Obtener detalle completo de una transcripcion.

    Args:
        transcription_id: UUID de la transcripcion.
        transcription_repo: Repositorio de transcripciones (inyectado).

    Returns:
        TranscriptionResponse: Transcripcion completa con texto.

    Raises:
        HTTPException 404: Si la transcripcion no existe.

    Example:
        GET /api/v1/transcriptions/123e4567-e89b-12d3-a456-426614174000
    """
    transcription = transcription_repo.get_by_id(transcription_id)
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription {transcription_id} not found",
        )

    return TranscriptionResponse.model_validate(transcription)
