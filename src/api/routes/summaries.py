"""
Router de Summaries - Endpoints para resumenes generados por IA.

Este modulo define 5 endpoints para gestion de resumenes:
1. GET  /summaries              - Listar resumenes (paginado)
2. GET  /summaries/{id}         - Obtener detalle de resumen
3. POST /summaries/search       - Busqueda full-text en resumenes
4. GET  /videos/{video_id}/summary - Resumen de un video especifico
5. DELETE /summaries/{id}       - Eliminar resumen

Los resumenes son generados por DeepSeek API a partir de las transcripciones.
Incluyen puntos clave, temas y texto completo del resumen.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.dependencies import SummaryRepo
from src.api.schemas.common import CursorInfo
from src.api.schemas.summaries import (
    SummaryListResponse,
    SummaryResponse,
    SummarySearchRequest,
    SummarySearchResponse,
    SummarySearchResult,
)

# ==================== ROUTER ====================

router = APIRouter(prefix="/summaries", tags=["Summaries"])


# ==================== ENDPOINTS ====================


@router.get(
    "",
    response_model=SummaryListResponse,
    summary="List summaries",
    description="List all summaries with cursor-based pagination.",
    responses={
        200: {
            "description": "List of summaries with pagination",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "transcription_id": "987fcdeb-51a2-43f7-9876-543210987654",
                                "title": "FastAPI Best Practices",
                                "summary_text": "This video covers best practices for building APIs with FastAPI...",
                                "key_points": [
                                    "Use dependency injection",
                                    "Implement proper error handling",
                                ],
                                "topics": ["FastAPI", "Python", "API Design"],
                                "category": "framework",
                                "keywords": ["fastapi", "python", "async"],
                                "created_at": "2025-01-15T12:00:00Z",
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
def list_summaries(
    summary_repo: SummaryRepo,
    limit: int = Query(20, ge=1, le=100, description="Number of summaries to return"),
    cursor: UUID | None = Query(None, description="Cursor for pagination (last summary ID)"),
) -> SummaryListResponse:
    """
    Listar resumenes con paginacion cursor-based.

    Args:
        summary_repo: Repositorio de resumenes (inyectado).
        limit: Numero de resumenes a retornar (1-100, default 20).
        cursor: UUID del ultimo resumen (para paginacion).

    Returns:
        SummaryListResponse: Lista paginada de resumenes.

    Example:
        GET /api/v1/summaries?limit=20
        GET /api/v1/summaries?cursor=123e4567-e89b-12d3-a456-426614174000&limit=20
    """
    summaries = summary_repo.list_paginated(limit=limit, cursor=cursor)

    # Determinar si hay mas elementos
    has_next = len(summaries) == limit
    next_cursor = summaries[-1].id if has_next and summaries else None

    # Convertir a schemas
    summary_responses = [SummaryResponse.model_validate(s) for s in summaries]

    return SummaryListResponse(
        data=summary_responses,
        cursor=CursorInfo(
            has_next=has_next,
            next_cursor=next_cursor,
            count=len(summary_responses),
        ),
    )


@router.get(
    "/{summary_id}",
    response_model=SummaryResponse,
    summary="Get summary details",
    description="Get full summary text, key points, and topics by ID.",
)
def get_summary(
    summary_id: UUID,
    summary_repo: SummaryRepo,
) -> SummaryResponse:
    """
    Obtener detalle completo de un resumen.

    Args:
        summary_id: UUID del resumen.
        summary_repo: Repositorio de resumenes (inyectado).

    Returns:
        SummaryResponse: Resumen completo con texto y puntos clave.

    Raises:
        HTTPException 404: Si el resumen no existe.

    Example:
        GET /api/v1/summaries/123e4567-e89b-12d3-a456-426614174000
    """
    summary = summary_repo.get_by_id(summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary {summary_id} not found",
        )

    return SummaryResponse.model_validate(summary)


@router.post(
    "/search",
    response_model=SummarySearchResponse,
    summary="Search summaries",
    description="Full-text search in summaries using PostgreSQL full-text search.",
    responses={
        200: {
            "description": "Search results with relevance scoring",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "summary": {
                                    "id": "123e4567-e89b-12d3-a456-426614174000",
                                    "title": "FastAPI Best Practices",
                                    "summary_text": "This video covers best practices...",
                                    "key_points": ["Use dependency injection"],
                                    "topics": ["FastAPI", "Python"],
                                    "category": "framework",
                                },
                                "relevance_score": 0.95,
                            }
                        ],
                        "cursor": {"has_next": False, "next_cursor": None, "count": 1},
                        "query": "FastAPI best practices",
                    }
                }
            },
        }
    },
)
def search_summaries(
    search_request: SummarySearchRequest,
    summary_repo: SummaryRepo,
) -> SummarySearchResponse:
    """
    Busqueda full-text en resumenes.

    Busca en title, summary_text, key_points y topics usando
    PostgreSQL full-text search con ranking por relevancia.

    Args:
        search_request: Query de busqueda y parametros de paginacion.
        summary_repo: Repositorio de resumenes (inyectado).

    Returns:
        SummarySearchResponse: Resultados ordenados por relevancia.

    Example:
        POST /api/v1/summaries/search
        {
            "query": "machine learning neural networks",
            "limit": 20,
            "cursor": null
        }
    """
    results = summary_repo.search_full_text(
        query=search_request.query,
        limit=search_request.limit,
        cursor=search_request.cursor,
    )

    # Determinar si hay mas elementos
    has_next = len(results) == search_request.limit
    next_cursor = results[-1]["id"] if has_next and results else None

    # Convertir a schemas con relevance_score
    search_results = [
        SummarySearchResult(
            **SummaryResponse.model_validate(r["summary"]).model_dump(),
            relevance_score=r["relevance_score"],
        )
        for r in results
    ]

    return SummarySearchResponse(
        data=search_results,
        cursor=CursorInfo(
            has_next=has_next,
            next_cursor=next_cursor,
            count=len(search_results),
        ),
    )


@router.delete(
    "/{summary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete summary",
    description="Delete a summary (hard delete).",
)
def delete_summary(
    summary_id: UUID,
    summary_repo: SummaryRepo,
) -> None:
    """
    Eliminar un resumen.

    Args:
        summary_id: UUID del resumen a eliminar.
        summary_repo: Repositorio de resumenes (inyectado).

    Returns:
        None: 204 No Content si exitoso.

    Raises:
        HTTPException 404: Si el resumen no existe.

    Example:
        DELETE /api/v1/summaries/123e4567-e89b-12d3-a456-426614174000
    """
    summary = summary_repo.get_by_id(summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary {summary_id} not found",
        )

    summary_repo.delete(summary_id)  # type: ignore
    return None
