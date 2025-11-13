"""add_skipped_status_to_video_status_enum

Añade el valor 'skipped' al enum video_status para marcar
videos descartados por criterios (duración excesiva, etc.).

Revision ID: 79dac5ed9f40
Revises: dc8586fe118a
Create Date: 2025-11-13 11:55:25.316222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79dac5ed9f40'
down_revision: Union[str, Sequence[str], None] = 'dc8586fe118a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Añade el valor 'skipped' al enum video_status.

    PostgreSQL permite añadir valores a ENUMs existentes sin recrear la tabla.
    IF NOT EXISTS previene errores si el valor ya existe.
    """
    op.execute("ALTER TYPE video_status ADD VALUE IF NOT EXISTS 'skipped'")


def downgrade() -> None:
    """
    Downgrade de ENUMs en PostgreSQL es complejo.

    Requiere recrear el tipo enum, lo cual implica:
    1. Crear nuevo enum sin 'skipped'
    2. Convertir columna al nuevo tipo
    3. Eliminar enum antiguo
    4. Renombrar nuevo enum

    Como no es una operación crítica y puede causar downtime,
    esta migración es efectivamente irreversible en producción.
    """
    # No implementado intencionalmente
    # Si necesitas revertir, usa:
    # op.execute("UPDATE videos SET status = 'failed' WHERE status = 'skipped'")
    # y luego recrea el enum manualmente
    pass
