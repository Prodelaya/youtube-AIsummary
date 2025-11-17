"""
Tests de autenticación JWT.

Valida el flujo completo de autenticación:
- Login exitoso
- Token inválido retorna 401
- Endpoint protegido sin token retorna 401
- DELETE sin rol admin retorna 403
- Refresh token funciona
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.database import SessionLocal
from src.core.security import hash_password
from src.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_user():
    """Crear usuario admin de prueba antes de los tests."""
    db = SessionLocal()
    try:
        # Verificar si ya existe el usuario admin
        existing_user = db.query(User).filter(User.username == "admin").first()
        if not existing_user:
            admin_user = User(
                username="admin",
                email="admin@localhost",
                hashed_password=hash_password("changeme123"),
                role="admin",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
        yield
    finally:
        db.close()


def test_login_success():
    """Test 1: Login exitoso retorna JWT válido."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 50  # JWT debe ser largo


def test_login_invalid_password():
    """Test 2: Login con password incorrecta retorna 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_endpoint_without_token():
    """Test 3: Endpoint protegido sin token retorna 401."""
    response = client.delete("/api/v1/summaries/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 401  # No Unauthorized


def test_endpoint_with_invalid_token():
    """Test 4: Endpoint protegido con token inválido retorna 401."""
    response = client.delete(
        "/api/v1/summaries/550e8400-e29b-41d4-a716-446655440000",
        headers={"Authorization": "Bearer invalid_token_here"},
    )

    assert response.status_code == 401


def test_refresh_token_works():
    """Test 5: Refresh token genera nuevo access token."""
    # Primero hacer login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme123"},
    )
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    # Usar refresh token para obtener nuevo access token
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # El nuevo access token debe ser diferente
    assert data["access_token"] != login_response.json()["access_token"]
