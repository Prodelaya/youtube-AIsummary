"""
Modelo User para autenticación y autorización.

Este módulo define el modelo de usuario que gestiona la autenticación JWT
y control de acceso basado en roles (RBAC).
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    Modelo de usuario para autenticación y autorización.

    Gestiona credenciales, roles y estado de usuarios del sistema.
    Se utiliza para autenticación JWT y control de acceso (RBAC).

    Attributes:
        id: Primary key auto-incremental.
        username: Nombre de usuario único (login).
        email: Email único del usuario.
        hashed_password: Contraseña hasheada con bcrypt (nunca almacenar plaintext).
        role: Rol del usuario para control de acceso (admin, user, bot).
        is_active: Indica si el usuario está activo (soft delete).
        created_at: Timestamp de creación (automático via TimestampMixin).
        updated_at: Timestamp de última modificación (automático via TimestampMixin).

    Notes:
        - Las contraseñas NUNCA se almacenan en texto plano, solo hash bcrypt.
        - El rol 'admin' tiene acceso completo (CRUD en todos los recursos).
        - El rol 'user' tiene acceso de solo lectura.
        - El rol 'bot' es para integraciones automáticas (Telegram, CI/CD).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
        comment="Primary key auto-incremental",
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Nombre de usuario único (usado para login)",
    )

    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Email único del usuario",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Contraseña hasheada con bcrypt (NUNCA almacenar plaintext)",
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
        comment="Rol del usuario: admin, user, bot",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indica si el usuario está activo (false = soft delete)",
    )

    def __repr__(self) -> str:
        """
        Representación string del usuario (para debugging).

        Returns:
            str: Representación legible del usuario.
        """
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
