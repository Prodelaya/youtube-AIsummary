"""
Configuración centralizada de la aplicación.

Este módulo gestiona todas las variables de entorno usando Pydantic Settings,
proporcionando validación automática, tipado estático y valores por defecto seguros.

La configuración se carga automáticamente desde el archivo .env en la raíz del proyecto.
"""

from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración global de la aplicación.

    Carga y valida variables de entorno desde .env.
    Proporciona acceso tipado y seguro a toda la configuración del sistema.

    Attributes:
        DATABASE_URL: URL de conexión a PostgreSQL (validada automáticamente).
        REDIS_URL: URL de conexión a Redis (validada automáticamente).
        APYHUB_TOKEN: Token de autenticación para ApyHub API.
        API_HOST: Host donde escucha el servidor FastAPI.
        API_PORT: Puerto donde escucha el servidor FastAPI.
        API_WORKERS: Número de workers para uvicorn en producción.
        ENVIRONMENT: Entorno de ejecución (development, staging, production).
        DEBUG: Activa modo debug (logs detallados, recargas automáticas).
        LOG_LEVEL: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """

    # ==================== BASE DE DATOS ====================
    DATABASE_URL: PostgresDsn = Field(
        description="URL de conexión a PostgreSQL",
        examples=["postgresql://user:pass@localhost:5432/dbname"],
    )

    # ==================== CACHE Y MENSAJERÍA ====================
    REDIS_URL: RedisDsn = Field(
        description="URL de conexión a Redis",
        examples=["redis://localhost:6379/0"],
    )

    # ==================== API KEYS ====================
    APYHUB_TOKEN: str = Field(
        min_length=10,
        description="Token de autenticación para ApyHub API (servicio de resúmenes)",
    )

    # ==================== CONFIGURACIÓN API ====================
    API_HOST: str = Field(
        default="0.0.0.0",
        description="Host donde escucha FastAPI (0.0.0.0 = todas las interfaces)",
    )

    API_PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Puerto TCP donde escucha FastAPI",
    )

    API_WORKERS: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Número de workers Uvicorn en producción",
    )

    # ==================== APLICACIÓN ====================
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Entorno de ejecución (afecta logs, debug, optimizaciones)",
    )

    DEBUG: bool = Field(
        default=True,
        description="Activa modo debug (NUNCA en producción)",
    )

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Nivel de verbosidad de logs",
    )

    # ==================== CONFIGURACIÓN DE PYDANTIC ====================
    model_config = SettingsConfigDict(
        env_file=".env",  # Archivo desde donde cargar variables
        env_file_encoding="utf-8",  # Codificación del archivo .env
        case_sensitive=True,  # DATABASE_URL != database_url
        extra="ignore",  # Ignorar variables extra en .env (no fallar)
    )

    # ==================== VALIDADORES CUSTOM ====================
    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def validate_database_url(cls, value: PostgresDsn) -> str:
        """
        Convierte PostgresDsn a string para compatibilidad con SQLAlchemy.

        Args:
            value: URL de PostgreSQL validada por Pydantic.

        Returns:
            URL como string limpia para SQLAlchemy.
        """
        return str(value)

    @field_validator("REDIS_URL", mode="after")
    @classmethod
    def validate_redis_url(cls, value: RedisDsn) -> str:
        """
        Convierte RedisDsn a string para compatibilidad con Redis client.

        Args:
            value: URL de Redis validada por Pydantic.

        Returns:
            URL como string limpia para cliente Redis.
        """
        return str(value)

    # ==================== PROPIEDADES DERIVADAS ====================
    @property
    def is_production(self) -> bool:
        """
        Indica si la aplicación está en producción.

        Returns:
            True si ENVIRONMENT es 'production', False en caso contrario.
        """
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """
        Indica si la aplicación está en desarrollo.

        Returns:
            True si ENVIRONMENT es 'development', False en caso contrario.
        """
        return self.ENVIRONMENT == "development"


# ==================== INSTANCIA GLOBAL (SINGLETON) ====================
settings = Settings()  # type: ignore[call-arg]
