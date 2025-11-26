"""add 

  telegram fields to summary

Revision ID: 008143b48b22
Revises: efc32c8c8df9
Create Date: 2025-11-11 15:32:34.448235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008143b48b22'
down_revision: Union[str, Sequence[str], None] = 'efc32c8c8df9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar nuevas columnas para integración con Telegram Bot
    op.add_column(
        'summaries',
        sa.Column(
            'sent_to_telegram',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Si el resumen ya fue enviado al bot de Telegram'
        )
    )

    op.add_column(
        'summaries',
        sa.Column(
            'sent_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp de cuándo se envió a Telegram'
        )
    )

    op.add_column(
        'summaries',
        sa.Column(
            'telegram_message_ids',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='IDs de mensajes de Telegram donde se envió (formato: {chat_id: message_id})'
        )
    )

    # Crear índice para optimizar consultas de envío
    op.create_index(
        'ix_summaries_sent_to_telegram',
        'summaries',
        ['sent_to_telegram'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar índice primero
    op.drop_index('ix_summaries_sent_to_telegram', table_name='summaries')

    # Eliminar columnas de Telegram
    op.drop_column('summaries', 'telegram_message_ids')
    op.drop_column('summaries', 'sent_at')
    op.drop_column('summaries', 'sent_to_telegram')
