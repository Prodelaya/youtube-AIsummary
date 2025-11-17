"""
Schemas Pydantic para autenticación y autorización.

Define los modelos de entrada/salida para endpoints de auth.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request body para login con username/password."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Nombre de usuario",
        examples=["admin"],
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Contraseña en texto plano",
        examples=["changeme123"],
    )


class TokenResponse(BaseModel):
    """Response body para login exitoso."""

    access_token: str = Field(
        ...,
        description="JWT access token para autenticar peticiones",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGci..."],
    )

    refresh_token: str = Field(
        ...,
        description="JWT refresh token para renovar access token",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGci..."],
    )

    token_type: str = Field(
        default="bearer",
        description="Tipo de token (siempre 'bearer')",
    )


class RefreshTokenRequest(BaseModel):
    """Request body para renovar access token con refresh token."""

    refresh_token: str = Field(
        ...,
        description="Refresh token válido obtenido en el login",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGci..."],
    )


class UserResponse(BaseModel):
    """Response body con información del usuario actual."""

    id: int = Field(..., description="ID del usuario")
    username: str = Field(..., description="Nombre de usuario")
    email: str = Field(..., description="Email del usuario")
    role: str = Field(..., description="Rol del usuario (admin, user, bot)")
    is_active: bool = Field(..., description="Si el usuario está activo")

    class Config:
        """Configuración de Pydantic."""

        from_attributes = True  # Permite crear desde modelos SQLAlchemy
