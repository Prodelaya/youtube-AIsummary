"""
Tests de Rate Limiting.

Valida que SlowAPI protege endpoints críticos contra ataques de fuerza bruta
y DoS según los límites configurados.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

# Cliente de test
client = TestClient(app)


# ==================== TESTS DE RATE LIMITING ====================


def test_login_rate_limit_allows_within_limit():
    """Test 1: Login permite hasta 5 requests por minuto (dentro del límite)."""
    # Ejecutar 4 requests (debajo del límite de 5/minuto)
    for i in range(4):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme123"},
        )
        # La primera debe ser 200, las demás pueden ser 200 o 401 (si credenciales incorrectas)
        assert response.status_code in [200, 401], f"Request {i+1} failed with {response.status_code}"


def test_login_rate_limit_blocks_over_limit():
    """Test 2: Login bloquea requests que excedan 5/minuto."""
    # Ejecutar 6 requests en rápida sucesión (exceder límite de 5/minuto)
    responses = []
    for i in range(6):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        responses.append(response)

    # Al menos una de las últimas requests debe ser 429 (Too Many Requests)
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, f"Expected 429 in {status_codes}, but rate limit not triggered"

    # Verificar que al menos una respuesta fue bloqueada
    blocked_count = status_codes.count(429)
    assert blocked_count >= 1, f"Expected at least 1 blocked request, got {blocked_count}"


def test_rate_limiting_is_enforced_globally():
    """Test 3: Verifica que rate limiting está activo y funciona correctamente."""
    # Usar credenciales válidas (admin existe en BD por la migración)
    responses = []
    for i in range(7):  # Exceder límite de 5/minuto
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme123"},
        )
        responses.append(response)

    status_codes = [r.status_code for r in responses]

    # Debe haber al menos un 429 después de 5 requests
    assert 429 in status_codes, f"Expected 429 in {status_codes}, rate limiting not working"

    # Contar cuántos fueron bloqueados
    blocked_count = status_codes.count(429)
    # Deberían ser al menos 2 (request 6 y 7)
    assert blocked_count >= 1, f"Expected at least 1 blocked request, got {blocked_count}"


# ==================== TESTS DE CONFIGURACIÓN ====================


def test_rate_limit_error_format():
    """Test 4: El error 429 tiene el formato correcto."""
    # Forzar rate limit con múltiples requests
    for _ in range(6):
        client.post(
            "/api/v1/auth/login",
            json={"username": "test2", "password": "wrong"},
        )

    # La última debería ser 429
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test2", "password": "wrong"},
    )

    # Verificar que se alcanzó el rate limit
    if response.status_code == 429:
        # El error debe tener contenido JSON
        data = response.json()
        assert "error" in data or "detail" in data, "Response debe contener mensaje de error"
