"""
FastAPI Application Factory.

Este módulo define la aplicación principal de FastAPI siguiendo Clean Architecture.
Configura middlewares, routers, documentación y gestión de errores de forma centralizada.

La aplicación se inicializa mediante una función factory (create_app) para facilitar
testing y permitir diferentes configuraciones según el entorno (dev/staging/prod).
"""

# Built-in (estándar)
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

# Third-party (librerías externas)
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from starlette.exceptions import HTTPException as StarletteHTTPException

# Local (módulos propios)
from src.api.schemas.errors import ErrorResponse, ValidationErrorResponse
from src.core.config import settings
from src.services.downloader_service import (
    DownloadError,
    InvalidURLError,
    VideoNotAvailableError,
)
from src.services.summarization_service import SummarizationError
from src.services.transcription_service import TranscriptionError
from src.services.video_processing_service import (
    InvalidVideoStateError,
    VideoNotFoundError,
    VideoProcessingError,
)

# Importar routers
from src.api.routes import videos


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestiona el ciclo de vida de la aplicación FastAPI.

    Se ejecuta al inicio (startup) y al finalizar (shutdown) la aplicación.
    Útil para inicializar conexiones, cargar modelos, cerrar recursos, etc.

    Args:
        app: Instancia de la aplicación FastAPI.

    Yields:
        None: Cede el control mientras la aplicación está activa.

    Examples:
        Durante startup:
        - Inicializar pool de conexiones a BD
        - Cargar modelo Whisper en memoria
        - Verificar conectividad con Redis

        Durante shutdown:
        - Cerrar conexiones a BD
        - Liberar modelo Whisper de memoria
        - Limpiar archivos temporales
    """
    # ==================== STARTUP ====================
    print("🚀 Iniciando aplicación FastAPI...")
    print(f"📍 Entorno: {settings.ENVIRONMENT}")
    print(f"🔧 Debug: {settings.DEBUG}")
    print(f"📊 Log Level: {settings.LOG_LEVEL}")

    # TODO: Inicializar conexión a PostgreSQL
    # TODO: Inicializar conexión a Redis
    # TODO: Verificar conectividad con servicios externos

    print("✅ Aplicación iniciada correctamente")

    # ==================== APLICACIÓN ACTIVA ====================
    yield

    # ==================== SHUTDOWN ====================
    print("🛑 Cerrando aplicación FastAPI...")

    # TODO: Cerrar pool de conexiones a BD
    # TODO: Cerrar conexión a Redis
    # TODO: Limpiar recursos temporales

    print("✅ Aplicación cerrada correctamente")


def _get_api_description() -> str:
    """
    Genera la descripción de la API en formato Markdown.

    Returns:
        str: Descripción formateada para documentación OpenAPI.
    """
    return """
API REST para agregación inteligente de contenido sobre IA.

**Características principales:**
- 🎥 Scraping automático de canales YouTube
- 🎙️ Transcripción con Whisper (local, gratuito)
- 📝 Resúmenes con ApyHub API (IA)
- 🔍 Búsqueda full-text en resumenes
- 📊 Clasificación por temas y keywords

**Tecnologías:**
FastAPI · PostgreSQL · Redis · Celery · Whisper · Docker
"""


def create_app() -> FastAPI:
    """
    Factory function para crear la aplicación FastAPI.

    Esta función centraliza toda la configuración de la aplicación:
    - Metadata (título, descripción, versión)
    - Middlewares (CORS, seguridad)
    - Routers (endpoints)
    - Manejadores de errores
    - Documentación (Swagger/ReDoc)

    Returns:
        FastAPI: Instancia configurada de la aplicación.

    Notes:
        - Se usa una factory function (en lugar de instancia global) para facilitar testing.
        - Los tests pueden crear aplicaciones con configuraciones específicas.
        - Permite lazy loading de dependencias según entorno.

    Examples:
        >>> app = create_app()
        >>> # En tests:
        >>> test_app = create_app()  # Configuración aislada
    """
    # ==================== METADATA DE LA APLICACIÓN ====================
    app = FastAPI(
        title="YouTube AI Summary API",
        description=_get_api_description(),
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # ==================== MIDDLEWARES ====================

    # 1. CORS - Permitir peticiones desde frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Trusted Host - Prevenir ataques Host Header Injection
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.TRUSTED_HOSTS,
        )

    # ==================== MANEJADORES DE ERRORES ====================

    # 1. Excepciones de dominio: VideoNotFoundError
    @app.exception_handler(VideoNotFoundError)
    async def video_not_found_handler(request: Request, exc: VideoNotFoundError) -> JSONResponse:
        """Maneja VideoNotFoundError como 404 Not Found."""
        error = ErrorResponse(
            detail=str(exc),
            error_code="VIDEO_NOT_FOUND",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error.model_dump(),
        )

    # 2. Excepciones de dominio: InvalidVideoStateError
    @app.exception_handler(InvalidVideoStateError)
    async def invalid_video_state_handler(
        request: Request, exc: InvalidVideoStateError
    ) -> JSONResponse:
        """Maneja InvalidVideoStateError como 409 Conflict."""
        error = ErrorResponse(
            detail=str(exc),
            error_code="INVALID_VIDEO_STATE",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error.model_dump(),
        )

    # 3. Excepciones de servicios: InvalidURLError, VideoNotAvailableError
    @app.exception_handler(InvalidURLError)
    async def invalid_url_handler(request: Request, exc: InvalidURLError) -> JSONResponse:
        """Maneja InvalidURLError como 400 Bad Request."""
        error = ErrorResponse(
            detail=str(exc),
            error_code="INVALID_URL",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error.model_dump(),
        )

    @app.exception_handler(VideoNotAvailableError)
    async def video_not_available_handler(
        request: Request, exc: VideoNotAvailableError
    ) -> JSONResponse:
        """Maneja VideoNotAvailableError como 404 Not Found."""
        error = ErrorResponse(
            detail=str(exc),
            error_code="VIDEO_NOT_AVAILABLE",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error.model_dump(),
        )

    # 4. Excepciones de servicios: DownloadError, TranscriptionError, SummarizationError
    @app.exception_handler(DownloadError)
    async def download_error_handler(request: Request, exc: DownloadError) -> JSONResponse:
        """Maneja DownloadError como 500 Internal Server Error."""
        error = ErrorResponse(
            detail=f"Failed to download video: {str(exc)}",
            error_code="DOWNLOAD_ERROR",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error.model_dump(),
        )

    @app.exception_handler(TranscriptionError)
    async def transcription_error_handler(
        request: Request, exc: TranscriptionError
    ) -> JSONResponse:
        """Maneja TranscriptionError como 500 Internal Server Error."""
        error = ErrorResponse(
            detail=f"Failed to transcribe audio: {str(exc)}",
            error_code="TRANSCRIPTION_ERROR",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error.model_dump(),
        )

    @app.exception_handler(SummarizationError)
    async def summarization_error_handler(
        request: Request, exc: SummarizationError
    ) -> JSONResponse:
        """Maneja SummarizationError como 500 Internal Server Error."""
        error = ErrorResponse(
            detail=f"Failed to generate summary: {str(exc)}",
            error_code="SUMMARIZATION_ERROR",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error.model_dump(),
        )

    # 5. Excepciones genéricas de procesamiento
    @app.exception_handler(VideoProcessingError)
    async def video_processing_error_handler(
        request: Request, exc: VideoProcessingError
    ) -> JSONResponse:
        """Maneja VideoProcessingError como 500 Internal Server Error."""
        error = ErrorResponse(
            detail=str(exc),
            error_code="VIDEO_PROCESSING_ERROR",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error.model_dump(),
        )

    # 6. Excepciones HTTP estándar
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """
        Maneja excepciones HTTP estándar (404, 403, 500, etc.).

        Args:
            request: Petición HTTP que generó el error.
            exc: Excepción HTTP capturada.

        Returns:
            JSONResponse: Respuesta JSON estandarizada con ErrorResponse schema.
        """
        error = ErrorResponse(
            detail=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            metadata={"path": str(request.url)},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error.model_dump(),
        )

    # 7. Errores de validación Pydantic
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Maneja errores de validación de Pydantic.

        Args:
            request: Petición HTTP que generó el error.
            exc: Excepción de validación capturada.

        Returns:
            JSONResponse: Respuesta JSON con ValidationErrorResponse schema.
        """
        # Convertir errores de Pydantic a ErrorDetail
        from src.api.schemas.errors import ErrorDetail

        error_details = [
            ErrorDetail(
                loc=list(err["loc"]),
                msg=err["msg"],
                type=err["type"],
            )
            for err in exc.errors()
        ]

        validation_error = ValidationErrorResponse(detail=error_details)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=validation_error.model_dump(),
        )

    # 8. Excepciones no capturadas (catch-all)
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Maneja excepciones no capturadas (último recurso).

        Args:
            request: Petición HTTP que generó el error.
            exc: Excepción genérica capturada.

        Returns:
            JSONResponse: Respuesta JSON genérica de error interno.

        Notes:
            - En producción, NO expone detalles internos (seguridad).
            - En desarrollo, muestra traceback completo para debugging.
            - Todos los errores se loguean para análisis posterior.
        """
        # TODO: Loguear error con structlog
        # logger.error("Unhandled exception", exc_info=exc, request=request)

        error = ErrorResponse(
            detail="Internal Server Error" if settings.is_production else str(exc),
            error_code="INTERNAL_SERVER_ERROR",
            metadata={"path": str(request.url)} if settings.is_development else None,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error.model_dump(),
        )

    # ==================== ENDPOINTS BASE ====================

    @app.get("/", tags=["Root"])
    def root() -> dict[str, str]:
        """
        Endpoint raíz de bienvenida.

        Returns:
            dict: Mensaje de bienvenida con links útiles.

        Examples:
            GET /
            {
                "message": "YouTube AI Summary API",
                "version": "0.1.0",
                "docs": "/api/docs"
            }
        """
        return {
            "message": "YouTube AI Summary API",
            "version": "0.1.0",
            "docs": "/api/docs",
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        """
        Health check endpoint para monitoreo.

        Verifica que la aplicación está activa y responde correctamente.
        Útil para:
        - Load balancers (verificar si la instancia está viva)
        - Kubernetes liveness/readiness probes
        - Monitoreo con Prometheus/Grafana
        - Scripts de deployment

        Returns:
            dict: Estado de la aplicación.

        Examples:
            GET /health
            {
                "status": "ok",
                "environment": "development"
            }
        """
        # TODO: Verificar conexión a BD y Redis
        # TODO: Retornar 503 Service Unavailable si algún servicio crítico falla
        return {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
        }

    # ==================== PROMETHEUS METRICS ====================
    # Montar app de métricas en /metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # ==================== ROUTERS ====================
    app.include_router(videos.router, prefix="/api/v1")
    # TODO: Incluir routers restantes
    # app.include_router(transcriptions.router, prefix="/api/v1")
    # app.include_router(summaries.router, prefix="/api/v1")
    # app.include_router(stats.router, prefix="/api/v1")

    return app


# ==================== INSTANCIA GLOBAL ====================
# Esta instancia se usa en producción con Uvicorn
app = create_app()


# ==================== PUNTO DE ENTRADA (CLI) ====================
if __name__ == "__main__":
    """
    Punto de entrada para ejecución directa con Python.

    Útil solo para desarrollo rápido. En producción usar Uvicorn directamente:

        poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000

    Examples:
        Desarrollo:
        $ python -m src.api.main
        $ # O con Poetry:
        $ poetry run python -m src.api.main
    """
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.is_development,
    )
