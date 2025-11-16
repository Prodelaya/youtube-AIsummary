"""
Fixtures para tests de tareas Celery.

Proporciona fixtures comunes:
- db_session: Sesión de BD para tests de tasks
"""

import pytest
from sqlalchemy.orm import sessionmaker

from src.core.database import engine
from src.models.base import Base


@pytest.fixture(scope="function")
def db_session():
    """
    Crea una sesión de BD para tests de tasks.

    Cada test obtiene una BD limpia y aislada.
    Usa la BD real de desarrollo (requiere PostgreSQL corriendo).
    """
    # Crear todas las tablas (idempotente si ya existen)
    Base.metadata.create_all(engine)

    # Crear sesión
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        # Rollback para deshacer cambios del test
        session.rollback()
        session.close()

        # Limpiar datos pero mantener schema
        # Esto es más rápido y evita race conditions
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())

        # NO hacer drop_all aquí - causa race conditions entre tests
        # Base.metadata.drop_all(engine)
