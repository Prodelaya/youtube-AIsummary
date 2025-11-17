"""
Módulo de gestión de tokens JWT.

Proporciona funciones para crear y validar access tokens y refresh tokens
usando la librería python-jose.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from src.core.config import settings


def create_access_token(user_id: int, role: str, expires_delta: timedelta | None = None) -> str:
    """
    Crea un access token JWT para un usuario.

    Args:
        user_id: ID del usuario.
        role: Rol del usuario (admin, user, bot).
        expires_delta: Tiempo de expiración opcional (por defecto: config JWT_ACCESS_TOKEN_EXPIRE_MINUTES).

    Returns:
        str: Token JWT firmado.

    Notes:
        - El token incluye: user_id, role, exp (expiración), iat (issued at), jti (unique ID), type.
        - Firmado con HS256 + JWT_SECRET_KEY.
        - Cada token tiene un jti único para evitar colisiones.

    Examples:
        >>> token = create_access_token(user_id=1, role="admin")
        >>> # Token válido por 30 minutos (default)

        >>> token = create_access_token(user_id=1, role="admin", expires_delta=timedelta(hours=1))
        >>> # Token válido por 1 hora
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "user_id": user_id,
        "role": role,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),  # JWT ID único para cada token
        "type": "access",
    }

    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int, role: str) -> str:
    """
    Crea un refresh token JWT para renovar access tokens expirados.

    Args:
        user_id: ID del usuario.
        role: Rol del usuario (admin, user, bot).

    Returns:
        str: Refresh token JWT firmado.

    Notes:
        - Válido por JWT_REFRESH_TOKEN_EXPIRE_DAYS (default 7 días).
        - Solo se usa para obtener nuevos access tokens, no para acceso directo.
    """
    expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "user_id": user_id,
        "role": role,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),  # JWT ID único para cada token
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodifica y valida un access token JWT.

    Args:
        token: Token JWT a decodificar.

    Returns:
        dict: Payload del token (user_id, role, exp, etc.).

    Raises:
        JWTError: Si el token es inválido, expirado o manipulado.

    Notes:
        - Valida firma, expiración y formato automáticamente.
        - Lanza JWTError si cualquier validación falla.

    Examples:
        >>> payload = decode_access_token("eyJ0eXAiOiJKV1QiLCJhbGci...")
        >>> print(payload["user_id"])  # 1
        >>> print(payload["role"])     # "admin"
    """
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    # Validar que sea un access token (no refresh token)
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")

    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decodifica y valida un refresh token JWT.

    Args:
        token: Refresh token JWT a decodificar.

    Returns:
        dict: Payload del token (user_id, role, exp, etc.).

    Raises:
        JWTError: Si el token es inválido, expirado o manipulado.

    Notes:
        - Valida que sea tipo "refresh" (no "access").
    """
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    # Validar que sea un refresh token
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")

    return payload
