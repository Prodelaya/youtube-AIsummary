"""
Fixtures para tests de API.

Proporciona fixtures comunes para tests de endpoints:
- client: TestClient de FastAPI
- db_session: Sesion de BD para tests
- sample_data: Datos de prueba pre-cargados
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from src.api.dependencies import get_db
from src.api.main import app
from src.models.base import Base
from src.models.source import Source
from src.models.video import Video, VideoStatus

# ==================== DATABASE FIXTURES ====================


@pytest.fixture(scope="function")
def db_session():
    """
    Crea una sesion de BD para tests.

    Cada test obtiene una BD limpia y aislada.
    Usa la BD real de desarrollo (requiere PostgreSQL corriendo).
    """
    from src.core.database import engine

    # Crear todas las tablas (idempotente si ya existen)
    Base.metadata.create_all(engine)

    # Crear sesion
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


# ==================== FASTAPI CLIENT FIXTURE ====================


@pytest.fixture(scope="function")
def client(db_session: Session):
    """
    Crea un TestClient de FastAPI con BD de test.

    Override de la dependencia get_db para usar la sesion de test.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ==================== SAMPLE DATA FIXTURES ====================


@pytest.fixture(scope="function")
def sample_source(db_session: Session) -> Source:
    """Crea una fuente de ejemplo."""
    source = Source(
        name="Test Channel",
        url="https://youtube.com/@testchannel",
        source_type="youtube_channel",
        active=True,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture(scope="function")
def sample_video(db_session: Session, sample_source: Source) -> Video:
    """Crea un video de ejemplo."""
    video = Video(
        source_id=sample_source.id,
        youtube_id="test123456",
        title="Test Video",
        url="https://youtube.com/watch?v=test123456",
        duration_seconds=300,
        status=VideoStatus.PENDING,
        extra_metadata={"test": "data"},
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture(scope="function")
def sample_completed_video(db_session: Session, sample_source: Source) -> Video:
    """Crea un video completado de ejemplo."""
    video = Video(
        source_id=sample_source.id,
        youtube_id="completed123",
        title="Completed Video",
        url="https://youtube.com/watch?v=completed123",
        duration_seconds=600,
        status=VideoStatus.COMPLETED,
        extra_metadata={},
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video
