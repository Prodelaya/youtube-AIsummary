"""
Servicio de caché usando Redis.

Proporciona una capa de abstracción sobre Redis para operaciones de caché,
con soporte para serialización JSON, métricas de Prometheus, y fallback graceful.
"""

import hashlib
import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

from src.core.config import settings
from src.core.metrics import metrics

logger = logging.getLogger(__name__)

# ==================== TYPE VARS ====================

T = TypeVar("T")

# ==================== CONFIGURACIÓN ====================

# Redis DB 1 para caché (DB 0 es para Celery)
CACHE_DB = 1
CACHE_ENABLED = getattr(settings, "CACHE_ENABLED", True)
CACHE_DEFAULT_TTL = getattr(settings, "CACHE_DEFAULT_TTL", 3600)  # 1 hora por defecto

# Timeout para operaciones Redis (100ms)
REDIS_TIMEOUT = 0.1


# ==================== DECORADOR DE TIMING ====================


def timed(operation: str):
    """
    Decorador para medir duración de operaciones de caché.

    Args:
        operation: Nombre de la operación (get, set, delete, invalidate)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                metrics.cache_operation_duration_seconds.labels(operation=operation).observe(
                    duration
                )
                return result
            except Exception:
                duration = time.time() - start
                metrics.cache_operation_duration_seconds.labels(operation=operation).observe(
                    duration
                )
                raise

        return wrapper

    return decorator


# ==================== CACHE SERVICE ====================


class CacheService:
    """
    Servicio de caché con Redis.

    Proporciona métodos de alto nivel para operaciones de caché:
    - get(), set(), delete(): Operaciones básicas
    - exists(): Verificar existencia de key
    - get_or_set(): Patrón read-through
    - get_many(), set_many(): Operaciones batch
    - invalidate_pattern(): Invalidar múltiples keys por patrón
    - health_check(): Verificar estado de Redis

    Características:
    - Serialización automática JSON
    - Métricas de Prometheus
    - Logging estructurado
    - Fallback graceful ante errores Redis
    - Connection pooling automático
    """

    def __init__(self):
        """
        Inicializa el servicio de caché con pool de conexiones Redis.

        Raises:
            RedisConnectionError: Si no puede conectar a Redis y CACHE_ENABLED=True
        """
        self.enabled = CACHE_ENABLED
        self.redis_client = None

        if not self.enabled:
            logger.info("Cache disabled by configuration (CACHE_ENABLED=False)")
            return

        try:
            # Parsear REDIS_URL y cambiar a DB 1 para caché
            redis_url = str(settings.REDIS_URL).rsplit("/", 1)[0] + f"/{CACHE_DB}"

            # Crear pool de conexiones
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,  # Decodificar bytes a strings automáticamente
                socket_timeout=REDIS_TIMEOUT,
                socket_connect_timeout=REDIS_TIMEOUT,
                max_connections=20,  # Pool de conexiones
            )

            # Test de conexión
            self.redis_client.ping()
            logger.info(
                f"Cache service initialized successfully (Redis DB {CACHE_DB})",
                extra={"redis_url": redis_url, "cache_db": CACHE_DB},
            )

        except RedisConnectionError as e:
            logger.error(
                f"Failed to connect to Redis: {e}",
                exc_info=True,
                extra={"redis_url": str(settings.REDIS_URL)},
            )
            self.enabled = False
            self.redis_client = None
            metrics.cache_errors_total.labels(error_type="connection").inc()

    @timed("get")
    def get(self, key: str, cache_type: str = "generic") -> Any | None:
        """
        Obtiene valor de caché por key.

        Args:
            key: Clave de Redis
            cache_type: Tipo de caché para métricas (summary, user_recent, search, stats)

        Returns:
            Valor deserializado desde JSON, o None si no existe o hay error

        Example:
            summary_data = cache_service.get("summary:detail:123", cache_type="summary")
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)

            if value is None:
                metrics.cache_misses_total.labels(cache_type=cache_type).inc()
                logger.debug(
                    f"Cache miss: {key}",
                    extra={"key": key, "cache_type": cache_type},
                )
                return None

            # Deserializar JSON
            deserialized = json.loads(value)

            # Métricas
            metrics.cache_hits_total.labels(cache_type=cache_type).inc()
            metrics.cache_value_size_bytes.labels(cache_type=cache_type).observe(len(value))

            logger.debug(
                f"Cache hit: {key}",
                extra={
                    "key": key,
                    "cache_type": cache_type,
                    "value_size_bytes": len(value),
                },
            )

            return deserialized

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                f"Redis connection error on get: {e}",
                extra={"key": key, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="connection").inc()
            return None

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to deserialize cached value: {e}",
                exc_info=True,
                extra={"key": key, "value": value, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="serialization").inc()
            # Eliminar valor corrupto
            self.delete(key)
            return None

        except RedisError as e:
            logger.error(
                f"Redis error on get: {e}",
                exc_info=True,
                extra={"key": key, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="redis_error").inc()
            return None

    @timed("set")
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = CACHE_DEFAULT_TTL,
        cache_type: str = "generic",
    ) -> bool:
        """
        Almacena valor en caché con TTL.

        Args:
            key: Clave de Redis
            value: Valor a cachear (será serializado a JSON)
            ttl: Time-to-live en segundos (default: CACHE_DEFAULT_TTL)
            cache_type: Tipo de caché para métricas

        Returns:
            True si se almacenó correctamente, False si hubo error

        Example:
            cache_service.set("summary:detail:123", summary_dict, ttl=86400, cache_type="summary")
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            # Serializar a JSON
            serialized = json.dumps(value, default=str)  # default=str para UUIDs, datetimes

            # Almacenar con TTL
            self.redis_client.setex(key, ttl, serialized)

            # Métricas
            metrics.cache_value_size_bytes.labels(cache_type=cache_type).observe(len(serialized))

            logger.debug(
                f"Cache set: {key}",
                extra={
                    "key": key,
                    "cache_type": cache_type,
                    "ttl": ttl,
                    "value_size_bytes": len(serialized),
                },
            )

            return True

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                f"Redis connection error on set: {e}",
                extra={"key": key, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="connection").inc()
            return False

        except (TypeError, ValueError) as e:
            logger.error(
                f"Failed to serialize value for caching: {e}",
                exc_info=True,
                extra={"key": key, "value_type": type(value).__name__, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="serialization").inc()
            return False

        except RedisError as e:
            logger.error(
                f"Redis error on set: {e}",
                exc_info=True,
                extra={"key": key, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="redis_error").inc()
            return False

    @timed("delete")
    def delete(self, key: str) -> bool:
        """
        Elimina key de caché.

        Args:
            key: Clave de Redis a eliminar

        Returns:
            True si se eliminó, False si no existía o hubo error

        Example:
            cache_service.delete("summary:detail:123")
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            deleted_count = self.redis_client.delete(key)

            logger.debug(
                f"Cache delete: {key}",
                extra={"key": key, "deleted": deleted_count > 0},
            )

            return deleted_count > 0

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                f"Redis connection error on delete: {e}",
                extra={"key": key, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="connection").inc()
            return False

        except RedisError as e:
            logger.error(
                f"Redis error on delete: {e}",
                exc_info=True,
                extra={"key": key, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="redis_error").inc()
            return False

    def exists(self, key: str) -> bool:
        """
        Verifica si una key existe en caché.

        Args:
            key: Clave de Redis

        Returns:
            True si existe, False si no existe o hay error

        Example:
            if cache_service.exists("summary:detail:123"):
                ...
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            return self.redis_client.exists(key) > 0

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                f"Redis connection error on exists: {e}",
                extra={"key": key, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="connection").inc()
            return False

        except RedisError as e:
            logger.error(
                f"Redis error on exists: {e}",
                exc_info=True,
                extra={"key": key, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="redis_error").inc()
            return False

    @timed("get_or_set")
    def get_or_set(
        self,
        key: str,
        fetcher: Callable[[], T],
        ttl: int = CACHE_DEFAULT_TTL,
        cache_type: str = "generic",
    ) -> T | None:
        """
        Patrón read-through: obtiene de caché o ejecuta fetcher si no existe.

        Args:
            key: Clave de Redis
            fetcher: Función que obtiene el valor desde la fuente (ej: DB query)
            ttl: Time-to-live en segundos
            cache_type: Tipo de caché para métricas

        Returns:
            Valor desde caché o desde fetcher

        Example:
            summary = cache_service.get_or_set(
                key="summary:detail:123",
                fetcher=lambda: summary_repo.get_by_id(summary_id),
                ttl=86400,
                cache_type="summary"
            )
        """
        # Intentar obtener de caché
        cached = self.get(key, cache_type=cache_type)
        if cached is not None:
            return cached

        # Cache miss: ejecutar fetcher
        try:
            value = fetcher()

            if value is not None:
                # Almacenar en caché
                self.set(key, value, ttl=ttl, cache_type=cache_type)

            return value

        except Exception as e:
            logger.error(
                f"Fetcher failed in get_or_set: {e}",
                exc_info=True,
                extra={"key": key, "cache_type": cache_type, "error": str(e)},
            )
            return None

    def get_many(self, keys: list[str], cache_type: str = "generic") -> dict[str, Any]:
        """
        Obtiene múltiples valores de caché en una operación (batch).

        Args:
            keys: Lista de claves de Redis
            cache_type: Tipo de caché para métricas

        Returns:
            Diccionario {key: value} solo con keys que existían en caché

        Example:
            results = cache_service.get_many(
                ["summary:detail:123", "summary:detail:456"],
                cache_type="summary"
            )
        """
        if not self.enabled or not self.redis_client or not keys:
            return {}

        try:
            # Usar pipeline para batch operation
            pipe = self.redis_client.pipeline()
            for key in keys:
                pipe.get(key)

            values = pipe.execute()

            # Construir diccionario de resultados
            results = {}
            for key, value in zip(keys, values, strict=False):
                if value is not None:
                    try:
                        results[key] = json.loads(value)
                        metrics.cache_hits_total.labels(cache_type=cache_type).inc()
                    except json.JSONDecodeError:
                        logger.error(f"Failed to deserialize cached value for key: {key}")
                        metrics.cache_errors_total.labels(error_type="serialization").inc()
                else:
                    metrics.cache_misses_total.labels(cache_type=cache_type).inc()

            logger.debug(
                f"Cache get_many: {len(results)}/{len(keys)} hits",
                extra={
                    "total_keys": len(keys),
                    "hits": len(results),
                    "cache_type": cache_type,
                },
            )

            return results

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                f"Redis connection error on get_many: {e}",
                extra={"keys_count": len(keys), "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="connection").inc()
            return {}

        except RedisError as e:
            logger.error(
                f"Redis error on get_many: {e}",
                exc_info=True,
                extra={"keys_count": len(keys), "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="redis_error").inc()
            return {}

    def set_many(
        self,
        data: dict[str, Any],
        ttl: int = CACHE_DEFAULT_TTL,
        cache_type: str = "generic",
    ) -> bool:
        """
        Almacena múltiples valores en caché en una operación (batch).

        Args:
            data: Diccionario {key: value} a cachear
            ttl: Time-to-live en segundos (aplicado a todas las keys)
            cache_type: Tipo de caché para métricas

        Returns:
            True si se almacenó correctamente, False si hubo error

        Example:
            cache_service.set_many(
                {
                    "summary:detail:123": summary1_dict,
                    "summary:detail:456": summary2_dict
                },
                ttl=86400,
                cache_type="summary"
            )
        """
        if not self.enabled or not self.redis_client or not data:
            return False

        try:
            # Usar pipeline para batch operation
            pipe = self.redis_client.pipeline()
            for key, value in data.items():
                try:
                    serialized = json.dumps(value, default=str)
                    pipe.setex(key, ttl, serialized)
                except (TypeError, ValueError) as e:
                    logger.error(
                        f"Failed to serialize value for key {key}: {e}",
                        extra={"key": key, "error": str(e)},
                    )
                    metrics.cache_errors_total.labels(error_type="serialization").inc()
                    continue

            pipe.execute()

            logger.debug(
                f"Cache set_many: {len(data)} keys",
                extra={
                    "keys_count": len(data),
                    "ttl": ttl,
                    "cache_type": cache_type,
                },
            )

            return True

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                f"Redis connection error on set_many: {e}",
                extra={"keys_count": len(data), "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="connection").inc()
            return False

        except RedisError as e:
            logger.error(
                f"Redis error on set_many: {e}",
                exc_info=True,
                extra={"keys_count": len(data), "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="redis_error").inc()
            return False

    @timed("invalidate")
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalida (elimina) todas las keys que coincidan con un patrón.

        ADVERTENCIA: Usa comando KEYS de Redis, que es bloqueante.
        En producción con alto tráfico, considerar usar SCAN.

        Args:
            pattern: Patrón Redis (ej: "user:*:recent", "summary:*")

        Returns:
            Número de keys eliminadas

        Example:
            deleted_count = cache_service.invalidate_pattern("user:*:recent")
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            # Buscar keys que coincidan con patrón
            keys = self.redis_client.keys(pattern)

            if not keys:
                logger.debug(f"No keys found for pattern: {pattern}")
                return 0

            # Eliminar keys en batch
            deleted_count = self.redis_client.delete(*keys)

            logger.info(
                f"Cache invalidated by pattern: {pattern}",
                extra={
                    "pattern": pattern,
                    "deleted_count": deleted_count,
                },
            )

            return deleted_count

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                f"Redis connection error on invalidate_pattern: {e}",
                extra={"pattern": pattern, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="connection").inc()
            return 0

        except RedisError as e:
            logger.error(
                f"Redis error on invalidate_pattern: {e}",
                exc_info=True,
                extra={"pattern": pattern, "error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="redis_error").inc()
            return 0

    def health_check(self) -> dict[str, Any]:
        """
        Verifica el estado de Redis.

        Returns:
            Diccionario con estado de salud:
            {
                "status": "healthy" | "unhealthy",
                "latency_ms": float,
                "memory_used_mb": float,
                "keys_count": int,
                "enabled": bool
            }

        Example:
            health = cache_service.health_check()
            if health["status"] == "unhealthy":
                alert("Redis is down!")
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "enabled": False,
            }

        if not self.redis_client:
            return {
                "status": "unhealthy",
                "error": "Redis client not initialized",
                "enabled": True,
            }

        try:
            # Medir latency
            start = time.time()
            self.redis_client.ping()
            latency_ms = (time.time() - start) * 1000

            # Obtener info de memoria
            memory_info = self.redis_client.info("memory")
            memory_used_mb = memory_info["used_memory"] / 1024 / 1024

            # Contar keys en DB actual
            keys_count = self.redis_client.dbsize()

            return {
                "status": "healthy" if latency_ms < 100 else "degraded",
                "latency_ms": round(latency_ms, 2),
                "memory_used_mb": round(memory_used_mb, 2),
                "keys_count": keys_count,
                "enabled": True,
            }

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(
                f"Redis health check failed: {e}",
                exc_info=True,
                extra={"error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="connection").inc()
            return {
                "status": "unhealthy",
                "error": str(e),
                "enabled": True,
            }

        except RedisError as e:
            logger.error(
                f"Redis error on health check: {e}",
                exc_info=True,
                extra={"error": str(e)},
            )
            metrics.cache_errors_total.labels(error_type="redis_error").inc()
            return {
                "status": "unhealthy",
                "error": str(e),
                "enabled": True,
            }


# ==================== INSTANCIA SINGLETON ====================

cache_service = CacheService()


# ==================== UTILIDADES ====================


def hash_query(query: str) -> str:
    """
    Genera hash MD5 de una query para usar como key de caché.

    Normaliza la query (lowercase, strip, espacios múltiples) antes de hashear.

    Args:
        query: Query de búsqueda

    Returns:
        Hash MD5 hex (32 caracteres)

    Example:
        >>> hash_query("FastAPI Async")
        'a1b2c3d4e5f6...'
        >>> hash_query("fastapi async")  # Mismo hash
        'a1b2c3d4e5f6...'
        >>> hash_query("  fastapi   async  ")  # Mismo hash (normalizado)
        'a1b2c3d4e5f6...'
    """
    # Normalizar: lowercase, strip, y colapsar espacios múltiples
    normalized = " ".join(query.lower().split())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()
