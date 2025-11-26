"""create telegram_users table and subscriptions

Crea la tabla telegram_users para gestionar usuarios del bot de Telegram
y la tabla intermedia user_source_subscriptions para suscripciones M:N.

Revision ID: d189f0fc4824
Revises: 79dac5ed9f40
Create Date: 2025-11-26 10:52:00.349315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# revision identifiers, used by Alembic.
revision: str = 'd189f0fc4824'
down_revision: Union[str, Sequence[str], None] = '79dac5ed9f40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crear tabla telegram_users y user_source_subscriptions."""
    # Crear tabla telegram_users
    op.create_table(
        "telegram_users",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False, comment="Clave primaria (UUID v4)"),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            nullable=False,
            comment="ID único de Telegram del usuario",
        ),
        sa.Column(
            "username",
            sa.String(length=255),
            nullable=True,
            comment="Nombre de usuario de Telegram (@username)",
        ),
        sa.Column(
            "first_name",
            sa.String(length=255),
            nullable=True,
            comment="Nombre del usuario en Telegram",
        ),
        sa.Column(
            "last_name",
            sa.String(length=255),
            nullable=True,
            comment="Apellido del usuario en Telegram",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment="Si el usuario está activo en el bot",
        ),
        sa.Column(
            "language_code",
            sa.String(length=10),
            nullable=True,
            server_default='es',
            comment="Código ISO 639-1 del idioma del usuario",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp de cuándo se creó el registro",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp de cuándo se modificó por última vez",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )

    # Crear índices para telegram_users
    op.create_index("ix_telegram_users_telegram_id", "telegram_users", ["telegram_id"], unique=True)
    op.create_index("ix_telegram_users_username", "telegram_users", ["username"], unique=False)
    op.create_index("ix_telegram_users_is_active", "telegram_users", ["is_active"], unique=False)

    # Crear tabla intermedia M:N user_source_subscriptions
    op.create_table(
        "user_source_subscriptions",
        sa.Column(
            "user_id",
            PGUUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            PGUUID(as_uuid=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "source_id"),
    )


def downgrade() -> None:
    """Eliminar tablas telegram_users y user_source_subscriptions."""
    # Eliminar tabla intermedia primero (tiene FKs)
    op.drop_table("user_source_subscriptions")

    # Eliminar índices de telegram_users
    op.drop_index("ix_telegram_users_is_active", table_name="telegram_users")
    op.drop_index("ix_telegram_users_username", table_name="telegram_users")
    op.drop_index("ix_telegram_users_telegram_id", table_name="telegram_users")

    # Eliminar tabla telegram_users
    op.drop_table("telegram_users")
