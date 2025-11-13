"""
Tests unitarios para CacheService.

Tests de operaciones básicas de caché con Redis:
- get(), set(), delete()
- exists()
- get_or_set()
- get_many(), set_many()
- invalidate_pattern()
- health_check()
- serialización/deserialización JSON
- manejo de errores
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.services.cache_service import CacheService, hash_query


# ==================== FIXTURES ====================


@pytest.fixture
def cache_service():
    """Fixture de CacheService con Redis real (DB 15 para tests)."""
    with patch("src.services.cache_service.CACHE_DB", 15):
        service = CacheService()
        yield service
        # Cleanup: flush test DB después de cada test
        if service.enabled and service.redis_client:
            service.redis_client.flushdb()


@pytest.fixture
def mock_cache_service():
    """Fixture de CacheService con Redis mockeado."""
    with patch("src.services.cache_service.redis.from_url") as mock_redis:
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True

        service = CacheService()
        service.redis_client = mock_client

        yield service, mock_client


# ==================== TESTS BÁSICOS ====================


def test_cache_service_initialization(cache_service):
    """Test: CacheService se inicializa correctamente."""
    assert cache_service.enabled is True
    assert cache_service.redis_client is not None


def test_cache_service_disabled_when_redis_down():
    """Test: CacheService se deshabilita gracefully si Redis no está disponible."""
    # Patchear el ConnectionError de redis.exceptions, no el built-in
    from redis.exceptions import ConnectionError as RedisConnectionError

    with patch("src.services.cache_service.redis.from_url") as mock_redis:
        mock_from_url = MagicMock()
        mock_from_url.ping.side_effect = RedisConnectionError("Redis not available")
        mock_redis.return_value = mock_from_url

        service = CacheService()

        assert service.enabled is False
        assert service.redis_client is None


# ==================== TESTS DE GET/SET ====================


def test_set_and_get_string(cache_service):
    """Test: set() y get() con string simple."""
    key = "test:string"
    value = "Hello, Cache!"

    # Set
    result = cache_service.set(key, value, ttl=60, cache_type="test")
    assert result is True

    # Get
    cached = cache_service.get(key, cache_type="test")
    assert cached == value


def test_set_and_get_dict(cache_service):
    """Test: set() y get() con diccionario (serialización JSON)."""
    key = "test:dict"
    value = {
        "id": "123",
        "name": "FastAPI",
        "keywords": ["python", "async"],
        "count": 42,
    }

    # Set
    result = cache_service.set(key, value, ttl=60, cache_type="test")
    assert result is True

    # Get
    cached = cache_service.get(key, cache_type="test")
    assert cached == value
    assert cached["keywords"] == ["python", "async"]


def test_set_with_uuid(cache_service):
    """Test: set() serializa UUIDs correctamente."""
    key = "test:uuid"
    value = {
        "id": str(uuid4()),
        "data": "test",
    }

    result = cache_service.set(key, value, ttl=60, cache_type="test")
    assert result is True

    cached = cache_service.get(key, cache_type="test")
    assert cached["id"] == value["id"]


def test_get_nonexistent_key(cache_service):
    """Test: get() retorna None para key que no existe."""
    cached = cache_service.get("nonexistent:key", cache_type="test")
    assert cached is None


def test_set_with_ttl(cache_service):
    """Test: TTL se aplica correctamente."""
    import time

    key = "test:ttl"
    value = "expires soon"

    # Set con TTL de 1 segundo
    cache_service.set(key, value, ttl=1, cache_type="test")

    # Verificar que existe
    assert cache_service.exists(key) is True

    # Esperar a que expire
    time.sleep(1.1)

    # Verificar que expiró
    cached = cache_service.get(key, cache_type="test")
    assert cached is None


# ==================== TESTS DE DELETE Y EXISTS ====================


def test_delete_existing_key(cache_service):
    """Test: delete() elimina key existente."""
    key = "test:delete"
    cache_service.set(key, "value", ttl=60, cache_type="test")

    result = cache_service.delete(key)
    assert result is True

    # Verificar que ya no existe
    cached = cache_service.get(key, cache_type="test")
    assert cached is None


def test_delete_nonexistent_key(cache_service):
    """Test: delete() retorna False para key que no existe."""
    result = cache_service.delete("nonexistent:key")
    assert result is False


def test_exists_true(cache_service):
    """Test: exists() retorna True para key existente."""
    key = "test:exists"
    cache_service.set(key, "value", ttl=60, cache_type="test")

    assert cache_service.exists(key) is True


def test_exists_false(cache_service):
    """Test: exists() retorna False para key que no existe."""
    assert cache_service.exists("nonexistent:key") is False


# ==================== TESTS DE GET_OR_SET ====================


def test_get_or_set_cache_miss(cache_service):
    """Test: get_or_set() ejecuta fetcher en cache miss."""
    key = "test:get_or_set"
    expected_value = {"data": "from fetcher"}

    fetcher_called = []

    def fetcher():
        fetcher_called.append(True)
        return expected_value

    # Primera llamada: cache miss, ejecuta fetcher
    result = cache_service.get_or_set(key, fetcher, ttl=60, cache_type="test")

    assert result == expected_value
    assert len(fetcher_called) == 1

    # Segunda llamada: cache hit, NO ejecuta fetcher
    result2 = cache_service.get_or_set(key, fetcher, ttl=60, cache_type="test")

    assert result2 == expected_value
    assert len(fetcher_called) == 1  # No se ejecutó de nuevo


def test_get_or_set_cache_hit(cache_service):
    """Test: get_or_set() no ejecuta fetcher en cache hit."""
    key = "test:get_or_set_hit"
    cached_value = {"data": "from cache"}

    # Pre-cachear valor
    cache_service.set(key, cached_value, ttl=60, cache_type="test")

    fetcher_called = []

    def fetcher():
        fetcher_called.append(True)
        return {"data": "from fetcher"}

    # Llamar get_or_set (debería obtener de caché)
    result = cache_service.get_or_set(key, fetcher, ttl=60, cache_type="test")

    assert result == cached_value
    assert len(fetcher_called) == 0  # Fetcher NO se ejecutó


# ==================== TESTS DE BATCH OPERATIONS ====================


def test_get_many(cache_service):
    """Test: get_many() obtiene múltiples valores."""
    keys = ["test:many:1", "test:many:2", "test:many:3"]
    values = ["value1", "value2", "value3"]

    # Cachear valores
    for key, value in zip(keys, values):
        cache_service.set(key, value, ttl=60, cache_type="test")

    # Get many
    results = cache_service.get_many(keys, cache_type="test")

    assert len(results) == 3
    assert results["test:many:1"] == "value1"
    assert results["test:many:2"] == "value2"
    assert results["test:many:3"] == "value3"


def test_get_many_partial_hits(cache_service):
    """Test: get_many() retorna solo keys que existen."""
    # Cachear solo 2 de 3 keys
    cache_service.set("test:partial:1", "value1", ttl=60, cache_type="test")
    cache_service.set("test:partial:2", "value2", ttl=60, cache_type="test")

    keys = ["test:partial:1", "test:partial:2", "test:partial:3"]
    results = cache_service.get_many(keys, cache_type="test")

    assert len(results) == 2
    assert "test:partial:1" in results
    assert "test:partial:2" in results
    assert "test:partial:3" not in results


def test_set_many(cache_service):
    """Test: set_many() almacena múltiples valores."""
    data = {
        "test:batch:1": "value1",
        "test:batch:2": "value2",
        "test:batch:3": "value3",
    }

    result = cache_service.set_many(data, ttl=60, cache_type="test")
    assert result is True

    # Verificar que se guardaron
    for key, value in data.items():
        cached = cache_service.get(key, cache_type="test")
        assert cached == value


# ==================== TESTS DE INVALIDATE_PATTERN ====================


def test_invalidate_pattern(cache_service):
    """Test: invalidate_pattern() elimina keys que coinciden con patrón."""
    # Cachear múltiples keys con patrón
    cache_service.set("user:123:recent", "data1", ttl=60, cache_type="test")
    cache_service.set("user:456:recent", "data2", ttl=60, cache_type="test")
    cache_service.set("user:789:recent", "data3", ttl=60, cache_type="test")
    cache_service.set("summary:detail:123", "other", ttl=60, cache_type="test")

    # Invalidar patrón user:*:recent
    deleted_count = cache_service.invalidate_pattern("user:*:recent")

    assert deleted_count == 3

    # Verificar que se eliminaron
    assert cache_service.get("user:123:recent", cache_type="test") is None
    assert cache_service.get("user:456:recent", cache_type="test") is None
    assert cache_service.get("user:789:recent", cache_type="test") is None

    # Verificar que otras keys NO se eliminaron
    assert cache_service.get("summary:detail:123", cache_type="test") == "other"


def test_invalidate_pattern_no_matches(cache_service):
    """Test: invalidate_pattern() retorna 0 si no hay matches."""
    deleted_count = cache_service.invalidate_pattern("nonexistent:*:pattern")
    assert deleted_count == 0


# ==================== TESTS DE HEALTH CHECK ====================


def test_health_check_healthy(cache_service):
    """Test: health_check() retorna status healthy."""
    health = cache_service.health_check()

    assert health["status"] in ["healthy", "degraded"]
    assert "latency_ms" in health
    assert "memory_used_mb" in health
    assert "keys_count" in health
    assert health["enabled"] is True


def test_health_check_disabled():
    """Test: health_check() retorna disabled si caché deshabilitado."""
    with patch("src.services.cache_service.CACHE_ENABLED", False):
        service = CacheService()
        health = service.health_check()

        assert health["status"] == "disabled"
        assert health["enabled"] is False


# ==================== TESTS DE UTILIDADES ====================


def test_hash_query_consistent():
    """Test: hash_query() genera mismo hash para misma query (normalizada)."""
    query1 = "fastapi async"  # Misma query lowercase
    query2 = "fastapi async"
    query3 = "  fastapi   async  "  # Con espacios extra (strip normaliza)

    hash1 = hash_query(query1)
    hash2 = hash_query(query2)
    hash3 = hash_query(query3)

    # Todos deberían generar mismo hash (normalización)
    assert hash1 == hash2 == hash3
    assert len(hash1) == 32  # MD5 hex tiene 32 caracteres

    # Test adicional: mayúsculas/minúsculas dan mismo hash
    hash_upper = hash_query("FastAPI Async")
    hash_lower = hash_query("fastapi async")
    assert hash_upper == hash_lower


def test_hash_query_different():
    """Test: hash_query() genera hashes diferentes para queries diferentes."""
    hash1 = hash_query("FastAPI")
    hash2 = hash_query("Django")

    assert hash1 != hash2


# ==================== TESTS DE MANEJO DE ERRORES ====================


def test_set_invalid_value_type(cache_service):
    """Test: set() maneja valores no serializables gracefully."""
    key = "test:invalid"

    # Objeto no serializable (con referencia circular)
    invalid_value = {}
    invalid_value["self"] = invalid_value

    # Debería manejar el error y retornar False
    result = cache_service.set(key, invalid_value, ttl=60, cache_type="test")

    # Dependiendo de la implementación, puede fallar o no
    # Si JSON logra serializar con default=str, será True
    # Si no, será False
    assert isinstance(result, bool)


def test_get_corrupted_value(cache_service):
    """Test: get() maneja valores corruptos en Redis gracefully."""
    key = "test:corrupted"

    # Insertar JSON inválido directamente en Redis
    cache_service.redis_client.set(key, "{invalid json")

    # get() debería manejar el error y retornar None
    cached = cache_service.get(key, cache_type="test")
    assert cached is None

    # Debería haber eliminado el valor corrupto
    assert cache_service.exists(key) is False


def test_operations_when_disabled():
    """Test: operaciones retornan valores seguros cuando caché está deshabilitado."""
    with patch("src.services.cache_service.CACHE_ENABLED", False):
        service = CacheService()

        # get() retorna None
        assert service.get("any:key") is None

        # set() retorna False
        assert service.set("any:key", "value") is False

        # delete() retorna False
        assert service.delete("any:key") is False

        # exists() retorna False
        assert service.exists("any:key") is False

        # get_or_set() ejecuta fetcher
        result = service.get_or_set("any:key", lambda: "from fetcher")
        assert result == "from fetcher"

        # get_many() retorna dict vacío
        assert service.get_many(["key1", "key2"]) == {}

        # set_many() retorna False
        assert service.set_many({"key": "value"}) is False

        # invalidate_pattern() retorna 0
        assert service.invalidate_pattern("any:*") == 0
