"""
Dependencies de autenticación para FastAPI.

Proporciona dependencies reutilizables para proteger endpoints:
- get_current_user: Valida token JWT y retorna usuario
- require_admin: Requiere rol admin (hereda de get_current_user)
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from src.api.auth.jwt import decode_access_token
from src.api.dependencies import get_db
from src.models.user import User
from src.repositories.user_repository import UserRepository
from sqlalchemy.orm import Session

# OAuth2 scheme con Bearer token
# Los clientes deben enviar: Authorization: Bearer <token>
http_bearer = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Dependency que valida el token JWT y retorna el usuario actual.

    Args:
        credentials: Credenciales HTTP Bearer (token JWT).
        db: Sesión de base de datos.

    Returns:
        User: Usuario autenticado.

    Raises:
        HTTPException 401: Si el token es inválido, expirado o el usuario no existe.
        HTTPException 403: Si el usuario está inactivo.

    Examples:
        @router.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return {"username": current_user.username}
    """
    token = credentials.credentials

    # Intentar decodificar el token
    try:
        payload = decode_access_token(token)
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Buscar usuario en la base de datos
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    # Verificar que el usuario esté activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency que requiere que el usuario tenga rol 'admin'.

    Args:
        current_user: Usuario autenticado (obtenido de get_current_user).

    Returns:
        User: Usuario con rol admin.

    Raises:
        HTTPException 403: Si el usuario no tiene rol admin.

    Examples:
        @router.delete("/videos/{video_id}")
        async def delete_video(
            video_id: str,
            current_user: User = Depends(require_admin)
        ):
            # Solo admins pueden llegar aquí
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required.",
        )

    return current_user
