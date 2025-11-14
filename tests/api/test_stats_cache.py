"""
Tests E2E para endpoints de estadísticas con caché.

Valida headers de caché y comportamiento HIT/MISS.
"""

import pytest

from src.services.cache_service import cache_service

# ==================== FIXTURES ====================


@pytest.fixture(autouse=True)
def clear_stats_cache():
    """Limpia caché de stats antes y después de cada test."""
    if cache_service.enabled:
        cache_service.invalidate_pattern("stats:*")
    yield
    if cache_service.enabled:
        cache_service.invalidate_pattern("stats:*")


# ==================== TESTS DE GET /stats ====================


def test_stats_global_has_cache_headers(client):
    """Test: /stats retorna headers de caché."""
    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    assert "X-Cache-Status" in response.headers
    assert "X-Cache-TTL" in response.headers
    assert response.headers["X-Cache-Status"] in ["HIT", "MISS"]


def test_stats_global_cache_miss_on_first_request(client):
    """Test: Primer request debe ser cache MISS."""
    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    assert response.headers["X-Cache-Status"] == "MISS"
    assert int(response.headers["X-Cache-TTL"]) == 900


def test_stats_global_cache_hit_on_second_request(client):
    """Test: Segundo request debe ser cache HIT."""
    # Primer request
    response1 = client.get("/api/v1/stats")
    assert response1.headers["X-Cache-Status"] == "MISS"

    # Segundo request
    response2 = client.get("/api/v1/stats")
    assert response2.headers["X-Cache-Status"] == "HIT"


def test_stats_global_cache_bypass_with_header(client):
    """Test: X-Cache-Bypass fuerza MISS."""
    # Cachear primero
    client.get("/api/v1/stats")

    # Request con bypass
    response = client.get("/api/v1/stats", headers={"X-Cache-Bypass": "true"})

    assert response.status_code == 200
    assert response.headers["X-Cache-Status"] == "MISS"


def test_stats_global_data_consistency(client):
    """Test: Datos de cache HIT == datos frescos."""
    # Fresh data
    response1 = client.get("/api/v1/stats", headers={"X-Cache-Bypass": "true"})
    data1 = response1.json()

    # Cached data
    response2 = client.get("/api/v1/stats")
    data2 = response2.json()

    assert data1 == data2


# ==================== TESTS DE MÚLTIPLES REQUESTS ====================


def test_multiple_requests_use_same_cache(client):
    """Test: Múltiples requests usan el mismo caché."""
    # Primer request cachea
    response1 = client.get("/api/v1/stats")
    assert response1.headers["X-Cache-Status"] == "MISS"

    # 5 requests más deben ser HIT
    hit_count = 0
    for _ in range(5):
        response = client.get("/api/v1/stats")
        if response.headers["X-Cache-Status"] == "HIT":
            hit_count += 1

    assert hit_count == 5


def test_cache_bypass_values(client):
    """Test: Diferentes valores de X-Cache-Bypass."""
    # Cachear
    client.get("/api/v1/stats")

    # Probar diferentes valores de bypass
    for bypass_value in ["true", "1", "yes"]:
        response = client.get("/api/v1/stats", headers={"X-Cache-Bypass": bypass_value})
        assert response.headers["X-Cache-Status"] == "MISS", f"Failed with bypass={bypass_value}"

    # Valor que NO activa bypass
    response = client.get("/api/v1/stats", headers={"X-Cache-Bypass": "false"})
    assert response.headers["X-Cache-Status"] == "HIT"


# ==================== TESTS DE RESPONSE STRUCTURE ====================


def test_stats_response_has_expected_fields(client):
    """Test: Response de /stats tiene estructura correcta."""
    response = client.get("/api/v1/stats")
    data = response.json()

    # Campos requeridos
    assert "total_videos" in data
    assert "completed_videos" in data
    assert "failed_videos" in data
    assert "pending_videos" in data
    assert "total_transcriptions" in data
    assert "total_summaries" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)


def test_stats_source_list_structure(client):
    """Test: Lista de sources en /stats tiene estructura correcta."""
    response = client.get("/api/v1/stats")
    data = response.json()

    if len(data["sources"]) > 0:
        source = data["sources"][0]
        assert "source_id" in source
        assert "source_name" in source
        assert "total_videos" in source
        assert "completed_videos" in source
        assert "failed_videos" in source
        assert "pending_videos" in source
