"""
Configuración centralizada del sistema de logging estructurado.

Este módulo implementa logging JSON estructurado usando structlog para toda la aplicación.
Proporciona:
- Formato JSON consistente en todos los módulos
- Request ID para correlación entre operaciones relacionadas
- Procesadores para enriquecer contexto (timestamp, módulo, nivel)
- Filtrado de información sensible (tokens, passwords)
- Rotación automática de archivos de log
- Configuración diferenciada por entorno (dev/prod)

Example:
    >>> from src.core.logging_config import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("user_registered", user_id=123, email="user@example.com")
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, Processor

# ==================== CONFIGURACIÓN ====================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Archivos de log separados por componente
APP_LOG_FILE = LOG_DIR / "app.json"
CELERY_LOG_FILE = LOG_DIR / "celery.json"
BOT_LOG_FILE = LOG_DIR / "bot.json"

# Configuración de rotación
MAX_BYTES = 100 * 1024 * 1024  # 100MB
BACKUP_COUNT = 10  # Máximo 10 archivos (1GB total aprox)

# Lista de campos sensibles a filtrar
SENSITIVE_FIELDS = {
    "password",
    "token",
    "secret",
    "api_key",
    "authorization",
    "TELEGRAM_BOT_TOKEN",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
}


# ==================== PROCESADORES CUSTOM ====================


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Añade contexto de aplicación a cada log.

    Enriquece el log con información del módulo y proceso actual.

    Args:
        logger: Logger de structlog.
        method_name: Método del logger (info, error, etc.).
        event_dict: Diccionario del evento a loggear.

    Returns:
        EventDict enriquecido con contexto de aplicación.
    """
    # Extraer nombre del módulo del logger
    if hasattr(logger, "name"):
        event_dict["module"] = logger.name

    return event_dict


def filter_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Filtra información sensible de los logs.

    Reemplaza valores de campos sensibles (tokens, passwords, etc.)
    con '***' para evitar exponer credenciales en logs.

    Args:
        logger: Logger de structlog.
        method_name: Método del logger.
        event_dict: Diccionario del evento a loggear.

    Returns:
        EventDict con campos sensibles filtrados.
    """
    for key, value in event_dict.items():
        # Filtrar campos sensibles completos
        if key.lower() in {s.lower() for s in SENSITIVE_FIELDS}:
            event_dict[key] = "***"
            continue

        # Filtrar tokens en URLs (query params)
        if isinstance(value, str) and ("token=" in value or "api_key=" in value):
            # Sanitizar URLs: ?token=abc123 → ?token=***
            import re

            event_dict[key] = re.sub(
                r"(token|api_key|secret)=[^&\s]+",
                r"\1=***",
                value,
                flags=re.IGNORECASE,
            )

    return event_dict


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Añade Request ID al contexto de log si está disponible.

    El Request ID se obtiene del contexto de structlog (inyectado por middleware
    o context managers).

    Args:
        logger: Logger de structlog.
        method_name: Método del logger.
        event_dict: Diccionario del evento.

    Returns:
        EventDict con request_id si está disponible en el contexto.
    """
    # structlog context se maneja automáticamente con bind()
    # Este processor es un placeholder para lógica futura si es necesaria
    return event_dict


# ==================== CONFIGURACIÓN DE STRUCTLOG ====================


def configure_logging(env: str = "development", component: str = "app") -> None:
    """
    Configura el sistema de logging estructurado para toda la aplicación.

    Establece processors, handlers y formatos según el entorno y componente.

    Args:
        env: Entorno de ejecución ('development', 'production').
        component: Componente de la app ('app', 'celery', 'bot').

    Example:
        >>> configure_logging(env="production", component="celery")
    """
    # Seleccionar archivo de log según componente
    log_file_map = {
        "app": APP_LOG_FILE,
        "celery": CELERY_LOG_FILE,
        "bot": BOT_LOG_FILE,
    }
    log_file = log_file_map.get(component, APP_LOG_FILE)

    # Configurar logging estándar de Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Configurar handler de archivo con rotación
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)

    # Handler para consola (desarrollo)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if env == "development" else logging.INFO)

    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configurar structlog
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # Merge context variables
        structlog.stdlib.add_log_level,  # Añadir nivel de log
        structlog.stdlib.add_logger_name,  # Añadir nombre del logger
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # Timestamp ISO 8601 UTC
        add_app_context,  # Contexto de aplicación
        filter_sensitive_data,  # Filtrar datos sensibles
        add_request_id,  # Request ID (si está en contexto)
        structlog.processors.StackInfoRenderer(),  # Stack traces
        structlog.processors.format_exc_info,  # Formatear excepciones
    ]

    # Añadir processor final según entorno
    if env == "development":
        # Desarrollo: Formato legible con colores
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # Producción: JSON compacto
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ==================== FACTORY DE LOGGERS ====================


def get_logger(module_name: str) -> structlog.stdlib.BoundLogger:
    """
    Obtiene un logger estructurado para el módulo especificado.

    Factory function para crear loggers con configuración consistente.
    El logger devuelto soporta logging estructurado con bind() para
    añadir contexto.

    Args:
        module_name: Nombre del módulo (típicamente __name__).

    Returns:
        Logger estructurado de structlog.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_registered", user_id=123, email="user@example.com")
        >>> # Output JSON:
        >>> # {
        >>> #   "event": "user_registered",
        >>> #   "user_id": 123,
        >>> #   "email": "user@example.com",
        >>> #   "timestamp": "2025-11-15T14:30:45.123Z",
        >>> #   "level": "info",
        >>> #   "module": "src.services.user_service"
        >>> # }
    """
    return structlog.get_logger(module_name)


# ==================== INICIALIZACIÓN AUTOMÁTICA ====================

# Configurar logging al importar el módulo
# Detectar entorno desde variables o config
try:
    from src.core.config import settings

    env = "production" if settings.ENVIRONMENT == "production" else "development"
except ImportError:
    # Si no hay config disponible, usar desarrollo por defecto
    env = "development"

# Configurar con componente 'app' por defecto
# Los workers de Celery/Bot reconfigurarán con su componente específico
configure_logging(env=env, component="app")
