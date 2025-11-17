"""
Endpoints de autenticación y autorización.

Proporciona endpoints para login, refresh token y consulta de usuario actual.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from src.api.auth.dependencies import get_current_user
from src.api.auth.jwt import create_access_token, create_refresh_token, decode_refresh_token
from src.api.dependencies import get_db
from src.api.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from src.core.security import verify_password
from src.models.user import User
from src.repositories.user_repository import UserRepository

# Router para endpoints de autenticación
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Limiter para rate limiting (compartido desde main.py via app.state)
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login con username y password",
    description="Autentica un usuario y retorna access token + refresh token JWT.",
)
@limiter.limit("5/minute")  # Protección contra brute-force
def login(
    request: Request,
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """
    Endpoint de login con username y password.

    Args:
        credentials: Username y password del usuario.
        db: Sesión de base de datos.

    Returns:
        TokenResponse: Access token y refresh token JWT.

    Raises:
        HTTPException 401: Si las credenciales son incorrectas o el usuario no existe.

    Examples:
        POST /api/v1/auth/login
        {
            "username": "admin",
            "password": "changeme123"
        }

        Response 200:
        {
            "access_token": "eyJ0eXAi...",
            "refresh_token": "eyJ0eXAi...",
            "token_type": "bearer"
        }
    """
    user_repo = UserRepository(db)

    # Buscar usuario por username
    user = user_repo.get_by_username(credentials.username)

    # Validar que el usuario existe y la password es correcta
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validar que el usuario está activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Crear tokens JWT
    access_token = create_access_token(user_id=user.id, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id, role=user.role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Renovar access token con refresh token",
    description="Genera un nuevo access token usando un refresh token válido.",
)
def refresh_access_token(
    request: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """
    Endpoint para renovar access token usando refresh token.

    Args:
        request: Refresh token válido.
        db: Sesión de base de datos.

    Returns:
        TokenResponse: Nuevo access token y refresh token.

    Raises:
        HTTPException 401: Si el refresh token es inválido o expirado.

    Examples:
        POST /api/v1/auth/refresh
        {
            "refresh_token": "eyJ0eXAi..."
        }

        Response 200:
        {
            "access_token": "eyJ0eXAi...",  # Nuevo
            "refresh_token": "eyJ0eXAi...",  # Nuevo
            "token_type": "bearer"
        }
    """
    try:
        # Decodificar refresh token
        payload = decode_refresh_token(request.refresh_token)
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")

        if user_id is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verificar que el usuario sigue existiendo y está activo
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )

        # Crear nuevos tokens
        new_access_token = create_access_token(user_id=user_id, role=role)
        new_refresh_token = create_refresh_token(user_id=user_id, role=role)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario actual",
    description="Retorna información del usuario autenticado (basado en el token JWT).",
)
def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """
    Endpoint para obtener información del usuario actual.

    Args:
        current_user: Usuario autenticado (dependency).

    Returns:
        UserResponse: Información del usuario.

    Examples:
        GET /api/v1/auth/me
        Headers: Authorization: Bearer eyJ0eXAi...

        Response 200:
        {
            "id": 1,
            "username": "admin",
            "email": "admin@localhost",
            "role": "admin",
            "is_active": true
        }
    """
    return UserResponse.model_validate(current_user)
