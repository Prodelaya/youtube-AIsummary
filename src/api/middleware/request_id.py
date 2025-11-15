"""
Middleware para inyectar Request ID en cada request de FastAPI.

Este middleware:
- Genera un UUID único por cada request HTTP
- Inyecta el Request ID en el contexto de structlog
- Añade el header X-Request-ID en la respuesta
- Permite correlación de logs end-to-end

Example:
    >>> from fastapi import FastAPI
    >>> from src.api.middleware.request_id import RequestIDMiddleware
    >>> app = FastAPI()
    >>> app.add_middleware(RequestIDMiddleware)
"""

import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware para generar y propagar Request ID en cada request.

    El Request ID permite rastrear todas las operaciones relacionadas
    con un request específico a través de múltiples servicios y workers.

    Attributes:
        app: Aplicación FastAPI.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Procesa el request, inyectando Request ID en contexto y response.

        Args:
            request: Request HTTP entrante.
            call_next: Siguiente handler en la cadena.

        Returns:
            Response con header X-Request-ID.
        """
        # Generar Request ID único (o usar el proporcionado por el cliente)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Inyectar Request ID en contexto de structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Logging de inicio de request
        start_time = time.time()

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Procesar request
        try:
            response = await call_next(request)

            # Calcular duración
            duration_ms = int((time.time() - start_time) * 1000)

            # Logging de finalización de request
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Añadir Request ID al header de respuesta
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Logging de error
            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
                exc_info=True,
            )

            raise

        finally:
            # Limpiar contexto de structlog
            structlog.contextvars.clear_contextvars()
