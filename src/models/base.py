"""
Clase base para todos los modelos SQLAlchemy.

Este módulo define la DeclarativeBase de la que heredarán todos los modelos.
También incluye mixins para patrones comunes como timestamps y UUIDs.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Clase base para todos los modelos de base de datos.

    Todos los modelos de la aplicación heredan de esta clase.
    SQLAlchemy la usa para rastrear qué clases son modelos
    y cómo mapearlas a tablas de base de datos.

    Ejemplo:
        class Usuario(Base):
            __tablename__ = "usuarios"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    pass


class TimestampMixin:
    """
    Mixin que añade columnas de timestamp created_at y updated_at.

    Uso:
        class MiModelo(Base, TimestampMixin):
            __tablename__ = "mi_tabla"
            # ... otras columnas

    Los timestamps son:
    - created_at: Se establece una vez cuando se crea el registro (server_default)
    - updated_at: Se actualiza automáticamente en cada UPDATE (onupdate)
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # Función NOW() de PostgreSQL
        nullable=False,
        comment="Timestamp de cuándo se creó el registro",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # Auto-actualización en cada UPDATE
        nullable=False,
        comment="Timestamp de cuándo se modificó por última vez",
    )


class UUIDMixin:
    """
    Mixin que añade una columna de primary key UUID.

    Los UUIDs son mejores que enteros auto-incrementales para:
    - Sistemas distribuidos (sin colisiones entre diferentes servidores)
    - Seguridad (difícil adivinar el siguiente ID)
    - Merge de bases de datos (sin conflictos de IDs)

    Uso:
        class MiModelo(Base, UUIDMixin, TimestampMixin):
            __tablename__ = "mi_tabla"
            # No necesitas definir 'id', este mixin lo proporciona
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),  # Almacenar como UUID en PostgreSQL, no como string
        primary_key=True,
        default=uuid.uuid4,  # Generar UUID4 automáticamente en Python
        nullable=False,
        comment="Clave primaria (UUID v4)",
    )


class TimestampedUUIDBase(Base, UUIDMixin, TimestampMixin):
    """
    Clase base abstracta con UUID PK + timestamps.

    La mayoría de modelos heredarán de esta en lugar de Base directamente.
    Proporciona id, created_at y updated_at automáticamente.

    Uso:
        class MiModelo(TimestampedUUIDBase):
            __tablename__ = "mi_tabla"
            nombre: Mapped[str] = mapped_column(String(100))
            # id, created_at, updated_at son automáticos
    """

    __abstract__ = True  # SQLAlchemy no creará tabla para esta clase
