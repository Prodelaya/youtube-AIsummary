"""
Schemas comunes para respuestas de API.

Este modulo contiene schemas reutilizables:
- PaginatedResponse: Respuesta generica paginada
- MessageResponse: Respuesta simple con mensaje
- CursorInfo: Informacion de paginacion cursor-based
"""

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

# TypeVar para paginacion generica
T = TypeVar("T")


class MessageResponse(BaseModel):
    """
    Respuesta simple con un mensaje.

    Usado para operaciones que solo necesitan confirmar exito.

    Example:
        >>> response = MessageResponse(message="Video deleted successfully")
        >>> response.model_dump_json()
        '{"message": "Video deleted successfully"}'
    """

    message: str = Field(..., description="Mensaje descriptivo de la operacion")

    class Config:
        json_schema_extra = {"example": {"message": "Operation completed successfully"}}


class CursorInfo(BaseModel):
    """
    Informacion de paginacion cursor-based.

    Atributos:
        has_next: Si hay mas elementos despues del cursor actual.
        next_cursor: UUID del ultimo elemento (None si no hay mas).
        count: Numero de elementos retornados en esta pagina.
    """

    has_next: bool = Field(..., description="Indica si hay mas elementos disponibles")
    next_cursor: UUID | None = Field(
        None, description="UUID del siguiente cursor (None si es ultima pagina)"
    )
    count: int = Field(..., description="Numero de elementos en esta respuesta", ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "has_next": True,
                "next_cursor": "123e4567-e89b-12d3-a456-426614174000",
                "count": 20,
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Respuesta generica paginada con cursor-based pagination.

    Type Parameter:
        T: Tipo de los elementos en la lista data.

    Atributos:
        data: Lista de elementos (tipo generico).
        cursor: Informacion de paginacion.

    Example:
        >>> from src.api.schemas.videos import VideoResponse
        >>> response = PaginatedResponse[VideoResponse](
        ...     data=[video1, video2],
        ...     cursor=CursorInfo(has_next=True, next_cursor=video2.id, count=2)
        ... )
    """

    data: list[T] = Field(..., description="Lista de elementos de la pagina actual")
    cursor: CursorInfo = Field(..., description="Informacion de paginacion")

    class Config:
        # No podemos dar ejemplo generico aqui, se define en cada schema especifico
        pass
