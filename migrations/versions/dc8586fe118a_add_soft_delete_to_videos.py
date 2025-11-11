"""add_soft_delete_to_videos

Revision ID: dc8586fe118a
Revises: 008143b48b22
Create Date: 2025-11-11 22:23:36.122538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc8586fe118a'
down_revision: Union[str, Sequence[str], None] = '008143b48b22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agregar soft delete a la tabla videos.

    Agrega:
    - Campo deleted_at (TIMESTAMP with timezone, nullable)
    - Indice ix_videos_deleted_at para queries eficientes
    """
    # Agregar columna deleted_at
    op.add_column(
        'videos',
        sa.Column(
            'deleted_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Soft delete timestamp - NULL = activo, datetime = borrado'
        )
    )

    # Crear indice para filtrar videos activos/borrados
    op.create_index(
        'ix_videos_deleted_at',
        'videos',
        ['deleted_at'],
        unique=False
    )


def downgrade() -> None:
    """
    Revertir soft delete de la tabla videos.

    Elimina:
    - Indice ix_videos_deleted_at
    - Campo deleted_at
    """
    # Eliminar indice
    op.drop_index('ix_videos_deleted_at', table_name='videos')

    # Eliminar columna
    op.drop_column('videos', 'deleted_at')
