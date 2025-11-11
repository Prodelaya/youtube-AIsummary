"""
Fixtures compartidos para tests de integración.

Este archivo importa los fixtures de tests/repositories/conftest.py
para que estén disponibles en los tests de integración.
"""

# Importar todos los fixtures del conftest de repositories
from tests.repositories.conftest import (
    db_session,
    inactive_source,
    sample_source,
    sample_summary,
    sample_telegram_user,
    sample_transcription,
    sample_video,
    source_factory,
    summary_factory,
    telegram_user_factory,
    transcription_factory,
    video_factory,
)

# Re-exportar para que pytest los reconozca
__all__ = [
    "db_session",
    "sample_source",
    "inactive_source",
    "source_factory",
    "sample_video",
    "video_factory",
    "sample_transcription",
    "transcription_factory",
    "sample_summary",
    "summary_factory",
    "sample_telegram_user",
    "telegram_user_factory",
]
