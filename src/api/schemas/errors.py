"""
Schemas de errores para respuestas HTTP.

Define schemas para mensajes de error consistentes en toda la API,
siguiendo RFC 7807 Problem Details for HTTP APIs.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    Detalle de un error de validacion individual.

    Usado dentro de ValidationErrorResponse para mostrar errores
    especificos de campos.
    """

    loc: list[str | int] = Field(..., description="Ubicacion del error (campo/index)")
    msg: str = Field(..., description="Mensaje de error")
    type: str = Field(..., description="Tipo de error (ej: 'value_error.missing')")

    class Config:
        json_schema_extra = {
            "example": {
                "loc": ["body", "title"],
                "msg": "field required",
                "type": "value_error.missing",
            }
        }


class ValidationErrorResponse(BaseModel):
    """
    Respuesta de error de validacion (HTTP 422).

    Usado cuando los datos de entrada no cumplen con el schema.

    Example:
        >>> error = ValidationErrorResponse(
        ...     detail=[
        ...         ErrorDetail(
        ...             loc=["body", "title"],
        ...             msg="field required",
        ...             type="value_error.missing"
        ...         )
        ...     ]
        ... )
    """

    detail: list[ErrorDetail] = Field(
        ..., description="Lista de errores de validacion"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "detail": [
                    {
                        "loc": ["body", "title"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    },
                    {
                        "loc": ["body", "duration_seconds"],
                        "msg": "ensure this value is greater than 0",
                        "type": "value_error.number.not_gt",
                    },
                ]
            }
        }


class ErrorResponse(BaseModel):
    """
    Respuesta generica de error.

    Usado para errores HTTP 4xx y 5xx (excepto 422 que usa ValidationErrorResponse).

    Atributos:
        detail: Mensaje de error principal.
        error_code: Codigo de error interno (opcional, ej: 'VIDEO_NOT_FOUND').
        metadata: Informacion adicional contextual (opcional).

    Example:
        >>> error = ErrorResponse(
        ...     detail="Video not found",
        ...     error_code="VIDEO_NOT_FOUND",
        ...     metadata={"video_id": "123e4567-e89b-12d3-a456-426614174000"}
        ... )
    """

    detail: str = Field(..., description="Mensaje de error legible")
    error_code: str | None = Field(
        None, description="Codigo de error interno (ej: 'VIDEO_NOT_FOUND')"
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Datos adicionales del contexto del error"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Video not found in database",
                "error_code": "VIDEO_NOT_FOUND",
                "metadata": {"video_id": "123e4567-e89b-12d3-a456-426614174000"},
            }
        }
