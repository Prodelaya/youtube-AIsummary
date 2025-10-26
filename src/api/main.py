"""
FastAPI Application Factory.

Este módulo define la aplicación principal de FastAPI siguiendo Clean Architecture.
Configura middlewares, routers, documentación y gestión de errores de forma centralizada.

La aplicación se inicializa mediante una función factory (create_app) para facilitar
testing y permitir diferentes configuraciones según el entorno (dev/staging/prod).
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import settings

# Importar routers cuando existan
# from src.api.routes import health, sources, summaries


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

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """
        Maneja excepciones HTTP estándar (404, 403, 500, etc.).

        Args:
            request: Petición HTTP que generó el error.
            exc: Excepción HTTP capturada.

        Returns:
            JSONResponse: Respuesta JSON estandarizada con detalles del error.

        Examples:
            Error 404:
            {
                "error": {
                    "code": 404,
                    "message": "Not Found",
                    "detail": "Video no encontrado"
                }
            }
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "path": str(request.url),
                }
            },
        )

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
            JSONResponse: Respuesta JSON con detalles de campos inválidos.

        Examples:
            Request inválido:
            {
                "error": {
                    "code": 422,
                    "message": "Validation Error",
                    "details": [
                        {
                            "field": "email",
                            "message": "invalid email format",
                            "type": "value_error.email"
                        }
                    ]
                }
            }
        """
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": 422,
                    "message": "Validation Error",
                    "details": exc.errors(),
                }
            },
        )

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

        Examples:
            Error genérico en producción:
            {
                "error": {
                    "code": 500,
                    "message": "Internal Server Error"
                }
            }
        """
        # TODO: Loguear error con structlog
        # logger.error("Unhandled exception", exc_info=exc, request=request)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal Server Error",
                    # Solo mostrar detalles en desarrollo
                    "detail": str(exc) if settings.is_development else None,
                }
            },
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
    # TODO: Incluir routers cuando estén implementados
    # app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    # app.include_router(sources.router, prefix="/api/v1", tags=["Sources"])
    # app.include_router(summaries.router, prefix="/api/v1", tags=["Summaries"])

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
