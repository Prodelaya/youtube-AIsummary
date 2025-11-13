"""
Modelo TelegramUser - Representa usuarios del bot de Telegram.

Los usuarios de Telegram se registran automáticamente al interactuar con el bot.
Tienen una relación M:N con Source a través de la tabla intermedia
user_source_subscriptions (suscripciones).
"""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, ForeignKey, Index, String, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampedUUIDBase

# Import solo para type checking (no causa import circular)
if TYPE_CHECKING:
    from src.models.source import Source


# Tabla intermedia M:N para suscripciones usuario-fuente
user_source_subscriptions = Table(
    "user_source_subscriptions",
    Base.metadata,
    Column(
        "user_id",
        PGUUID(as_uuid=True),
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "source_id",
        PGUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # Constraint UNIQUE implícito por PRIMARY KEY compuesta
)


class TelegramUser(TimestampedUUIDBase):
    """
    Usuario de Telegram registrado en el bot.

    Almacena información básica del usuario de Telegram y gestiona
    sus suscripciones a fuentes (canales de YouTube) mediante relación M:N.

    Atributos:
        id: Clave primaria UUID (de TimestampedUUIDBase)
        telegram_id: ID único de Telegram (bigint, único)
        username: Nombre de usuario de Telegram (@username)
        first_name: Nombre del usuario
        last_name: Apellido del usuario (opcional)
        is_active: Si el usuario está activo (default True)
        language_code: Código de idioma del usuario ("es", "en", etc.)
        bot_blocked: Si el usuario bloqueó el bot o el chat no existe (default False)
        created_at: Timestamp de registro (de TimestampedUUIDBase)
        updated_at: Timestamp última modificación (de TimestampedUUIDBase)
        sources: Relación M:N con Source (fuentes suscritas)

    Ejemplos:
        >>> user = TelegramUser(
        ...     telegram_id=123456789,
        ...     username="john_doe",
        ...     first_name="John",
        ...     last_name="Doe",
        ...     language_code="en"
        ... )
    """

    __tablename__ = "telegram_users"

    # ==================== COLUMNAS ====================

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,  # Telegram IDs son bigint (pueden ser muy grandes)
        nullable=False,
        unique=True,  # Un telegram_id solo puede tener un registro
        comment="ID único de Telegram del usuario",
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,  # No todos los usuarios tienen @username
        comment="Nombre de usuario de Telegram (@username)",
    )

    first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nombre del usuario en Telegram",
    )

    last_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Apellido del usuario en Telegram",
    )

    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Si el usuario está activo en el bot",
    )

    language_code: Mapped[str | None] = mapped_column(
        String(10),  # Códigos ISO son cortos (ej: 'es', 'en-US')
        nullable=True,
        default="es",
        comment="Código ISO 639-1 del idioma del usuario",
    )

    bot_blocked: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="Usuario ha bloqueado el bot o chat no existe",
    )

    # ==================== RELACIONES ====================

    # Relación M:N con Source (fuentes suscritas)
    sources: Mapped[list["Source"]] = relationship(
        "Source",
        secondary=user_source_subscriptions,
        back_populates="users",
        lazy="selectin",  # Carga eager de las fuentes suscritas
    )

    # ==================== ÍNDICES ====================
    __table_args__ = (
        Index("ix_telegram_users_telegram_id", "telegram_id", unique=True),
        Index("ix_telegram_users_username", "username"),
        Index("ix_telegram_users_is_active", "is_active"),
    )

    # ==================== MÉTODOS ====================

    def __repr__(self) -> str:
        """Representación en string para debugging."""
        username_str = f"@{self.username}" if self.username else "no username"
        return (
            f"<TelegramUser(id={self.id}, telegram_id={self.telegram_id}, "
            f"username={username_str}, active={self.is_active})>"
        )

    def to_dict(self) -> dict:
        """
        Convertir modelo a diccionario.

        Útil para serialización JSON en respuestas de bot.

        Returns:
            dict: Representación en diccionario del usuario.
        """
        return {
            "id": str(self.id),
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "language_code": self.language_code,
            "bot_blocked": self.bot_blocked,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def full_name(self) -> str:
        """
        Obtener nombre completo del usuario.

        Returns:
            str: first_name + last_name, o solo first_name si no hay last_name.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or "Unknown User"

    @property
    def display_name(self) -> str:
        """
        Obtener nombre para mostrar en el bot.

        Prioridad: @username > full_name > telegram_id

        Returns:
            str: Mejor representación del usuario para mostrar.
        """
        if self.username:
            return f"@{self.username}"
        if self.first_name:
            return self.full_name
        return f"User {self.telegram_id}"

    @property
    def subscription_count(self) -> int:
        """
        Obtener número de suscripciones activas.

        Returns:
            int: Cantidad de fuentes a las que está suscrito.
        """
        return len(self.sources)

    @property
    def has_subscriptions(self) -> bool:
        """
        Verificar si el usuario tiene suscripciones activas.

        Returns:
            bool: True si está suscrito a al menos una fuente.
        """
        return len(self.sources) > 0
