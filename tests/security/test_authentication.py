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


def test_token_without_user_id():
    """Test 6: Token JWT sin user_id retorna 401."""
    from src.api.auth.jwt import create_access_token
    from jose import jwt
    from src.core.config import settings
    from datetime import datetime, timedelta, UTC

    # Crear token JWT malformado sin user_id
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=30)
    payload = {
        # "user_id": 1,  # Intencionalmente omitido
        "role": "admin",
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    malformed_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {malformed_token}"},
    )

    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.json()["detail"]


def test_inactive_user_login():
    """Test 7: Usuario inactivo no puede hacer login."""
    db = SessionLocal()
    try:
        # Crear usuario inactivo
        from src.core.security import hash_password

        inactive_user = User(
            username="inactive_user",
            email="inactive@localhost",
            hashed_password=hash_password("password123"),
            role="user",
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()

        # Intentar login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "inactive_user", "password": "password123"},
        )

        assert response.status_code == 403
        assert "Inactive user" in response.json()["detail"]

    finally:
        # Cleanup
        db.query(User).filter(User.username == "inactive_user").delete()
        db.commit()
        db.close()


def test_inactive_user_with_valid_token():
    """Test 8: Usuario con token válido pero cuenta inactiva retorna 403."""
    from src.api.auth.jwt import create_access_token

    db = SessionLocal()
    try:
        # Crear usuario activo, obtener token, luego desactivarlo
        from src.core.security import hash_password

        temp_user = User(
            username="temp_active",
            email="temp@localhost",
            hashed_password=hash_password("password123"),
            role="user",
            is_active=True,
        )
        db.add(temp_user)
        db.commit()
        db.refresh(temp_user)

        # Crear token mientras el usuario está activo
        token = create_access_token(user_id=temp_user.id, role=temp_user.role)

        # Desactivar usuario
        temp_user.is_active = False
        db.commit()

        # Intentar usar el token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "Inactive user" in response.json()["detail"]

    finally:
        # Cleanup
        db.query(User).filter(User.username == "temp_active").delete()
        db.commit()
        db.close()


def test_require_admin_with_non_admin_user():
    """Test 9: Endpoint que requiere admin rechaza usuarios normales."""
    from src.api.auth.jwt import create_access_token

    db = SessionLocal()
    try:
        # Crear usuario normal (no admin)
        from src.core.security import hash_password

        normal_user = User(
            username="normal_user",
            email="normal@localhost",
            hashed_password=hash_password("password123"),
            role="user",  # NO admin
            is_active=True,
        )
        db.add(normal_user)
        db.commit()
        db.refresh(normal_user)

        # Crear token para usuario normal
        token = create_access_token(user_id=normal_user.id, role=normal_user.role)

        # Intentar acceder a endpoint que requiere admin (ej: DELETE summary)
        response = client.delete(
            "/api/v1/summaries/550e8400-e29b-41d4-a716-446655440000",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    finally:
        # Cleanup
        db.query(User).filter(User.username == "normal_user").delete()
        db.commit()
        db.close()


def test_refresh_token_with_invalid_type():
    """Test 10: Usar access token como refresh token retorna 401."""
    # Login para obtener tokens
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]  # Access token, no refresh

    # Intentar usar access token en lugar de refresh token
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},  # Wrong type
    )

    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


def test_refresh_token_with_inactive_user():
    """Test 11: Refresh token de usuario inactivo retorna 403."""
    from src.api.auth.jwt import create_refresh_token

    db = SessionLocal()
    try:
        # Crear usuario activo
        from src.core.security import hash_password

        temp_user = User(
            username="temp_for_refresh",
            email="temp_refresh@localhost",
            hashed_password=hash_password("password123"),
            role="user",
            is_active=True,
        )
        db.add(temp_user)
        db.commit()
        db.refresh(temp_user)

        # Crear refresh token mientras está activo
        refresh_token = create_refresh_token(user_id=temp_user.id, role=temp_user.role)

        # Desactivar usuario
        temp_user.is_active = False
        db.commit()

        # Intentar usar refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 403
        assert "Inactive user" in response.json()["detail"]

    finally:
        # Cleanup
        db.query(User).filter(User.username == "temp_for_refresh").delete()
        db.commit()
        db.close()


def test_refresh_token_without_user_id():
    """Test 12: Refresh token sin user_id retorna 401."""
    from jose import jwt
    from src.core.config import settings
    from datetime import datetime, timedelta, UTC

    # Crear refresh token malformado sin user_id
    now = datetime.now(UTC)
    expire = now + timedelta(days=7)
    payload = {
        # "user_id": 1,  # Omitido intencionalmente
        "role": "admin",
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }
    malformed_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": malformed_token},
    )

    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


def test_get_current_user_endpoint():
    """Test 13: Endpoint /me retorna información del usuario autenticado."""
    # Reutilizar token creado directamente para evitar rate limit
    from src.api.auth.jwt import create_access_token

    db = SessionLocal()
    try:
        # Buscar usuario admin existente
        admin = db.query(User).filter(User.username == "admin").first()
        assert admin is not None

        # Crear token para admin
        access_token = create_access_token(user_id=admin.id, role=admin.role)

        # Obtener info del usuario
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert data["is_active"] is True

    finally:
        db.close()
