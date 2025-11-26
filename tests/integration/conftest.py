"""
Fixtures compartidos para tests de integración de API.

Este módulo proporciona fixtures para tests de integración que cubren:
- TestClient de FastAPI con BD real
- Autenticación JWT (admin, user normal)
- Base de datos PostgreSQL de tests
- Datos de ejemplo para endpoints

IMPORTANTE: Requiere PostgreSQL corriendo en Docker.
Ejecutar antes de los tests: docker-compose up -d postgres
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.api.auth.jwt import create_access_token
from src.api.dependencies import get_db  # ← Importar desde dependencies, no desde database
from src.api.main import create_app
from src.models import Base, Source, Summary, Transcription, User, Video
from src.models.video import VideoStatus

# ==================== CONFIGURACIÓN DE BD DE TESTS ====================

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://iamonitor:iamonitor_dev_password@localhost:5432/iamonitor_test",
)


# ==================== FIXTURES DE BASE DE DATOS ====================


@pytest.fixture(scope="session")
def db_engine_session():
    """
    Engine de PostgreSQL compartido para toda la sesión de tests de integración.

    Scope 'session' significa que se crea UNA VEZ para todos los tests.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    # Crear todas las tablas
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup: eliminar todas las tablas al finalizar sesión
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine_session) -> Session:
    """
    Sesión de BD con limpieza automática entre tests.

    Cada test obtiene una sesión limpia.
    """
    SessionLocal = sessionmaker(bind=db_engine_session)
    session = SessionLocal()

    # Limpiar todas las tablas antes del test
    try:
        session.execute(
            text(
                "TRUNCATE TABLE summaries, transcriptions, videos, sources, telegram_users, users CASCADE"
            )
        )
        session.commit()
    except Exception:
        session.rollback()

    try:
        yield session
        # Commit al final para asegurar que todos los datos de fixtures están persistidos
        session.commit()
    finally:
        # No hacer rollback aquí, solo close
        session.close()


# ==================== FIXTURES DE FASTAPI TESTCLIENT ====================


@pytest.fixture(scope="function")
def app(db_session):
    """
    Fixture que proporciona la aplicación FastAPI configurada para tests.

    Sobrescribe la dependencia get_db para usar la sesión de tests.
    """
    app = create_app()

    # Override de la dependencia de BD para usar la sesión de tests
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    return app


@pytest.fixture(scope="function")
def client(app):
    """
    Fixture que proporciona TestClient de FastAPI.

    Permite hacer requests HTTP reales a los endpoints.
    """
    return TestClient(app)


# ==================== FIXTURES DE AUTENTICACIÓN ====================


@pytest.fixture
def admin_user(db_session) -> User:
    """
    Usuario admin para tests de autenticación.

    Returns:
        User con rol admin y password hasheado.
    """
    user = User(
        username="admin_test",
        email="admin@test.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU8KQDpTMWBq",  # "password123"
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session) -> User:
    """Usuario normal (no admin) para tests de autorización."""
    user = User(
        username="user_test",
        email="user@test.com",
        hashed_password="$2b$12$hashed_password",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user) -> str:
    """
    Token JWT válido para usuario admin.

    Returns:
        JWT token string para usar en headers de autorización.
    """
    return create_access_token(user_id=admin_user.id, role=admin_user.role)


@pytest.fixture
def user_token(regular_user) -> str:
    """Token JWT válido para usuario normal."""
    return create_access_token(user_id=regular_user.id, role=regular_user.role)


@pytest.fixture
def auth_headers(admin_token) -> dict:
    """
    Headers HTTP con autenticación admin.

    Returns:
        Dict con header Authorization Bearer token.

    Example:
        response = client.get("/videos", headers=auth_headers)
    """
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_auth_headers(user_token) -> dict:
    """Headers HTTP con autenticación de usuario normal."""
    return {"Authorization": f"Bearer {user_token}"}


# ==================== FIXTURES DE DATOS - SOURCES ====================


@pytest.fixture
def sample_source(db_session) -> Source:
    """
    Fuente de YouTube de ejemplo para tests de integración.

    Returns:
        Source activa con metadata básica.
    """
    source = Source(
        name="Test Channel",
        source_type="youtube",
        url="https://youtube.com/@testchannel",
        active=True,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


# ==================== FIXTURES DE DATOS - VIDEOS ====================


@pytest.fixture
def sample_video(db_session, sample_source) -> Video:
    """
    Video de ejemplo en estado PENDING para tests de integración.

    Returns:
        Video asociado a sample_source.
    """
    video = Video(
        source_id=sample_source.id,
        youtube_id="test_video_123",
        title="Test Video",
        url="https://youtube.com/watch?v=test_video_123",
        duration_seconds=300,
        status=VideoStatus.PENDING,
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def completed_video(db_session, sample_source) -> Video:
    """Video en estado COMPLETED con transcripción y resumen."""
    video = Video(
        source_id=sample_source.id,
        youtube_id="completed_video_456",
        title="Completed Video",
        url="https://youtube.com/watch?v=completed_video_456",
        duration_seconds=600,
        status=VideoStatus.COMPLETED,
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    # Añadir transcripción
    transcription = Transcription(
        video_id=video.id, text="This is a test transcription", language="en", duration_seconds=600
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)

    # Añadir resumen
    summary = Summary(
        transcription_id=transcription.id,
        summary_text="This is a test summary",
        keywords=["test", "integration", "api"],
    )
    db_session.add(summary)
    db_session.commit()

    return video


@pytest.fixture
def multiple_videos(db_session, sample_source) -> list[Video]:
    """
    Lista de múltiples videos para tests de listado y paginación.

    Returns:
        Lista de 10 videos en diferentes estados.
    """
    videos = []
    statuses = [
        VideoStatus.PENDING,
        VideoStatus.DOWNLOADING,
        VideoStatus.TRANSCRIBING,
        VideoStatus.SUMMARIZING,
        VideoStatus.COMPLETED,
        VideoStatus.FAILED,
        VideoStatus.SKIPPED,
        VideoStatus.PENDING,
        VideoStatus.COMPLETED,
        VideoStatus.PENDING,
    ]

    for i, status in enumerate(statuses):
        video = Video(
            source_id=sample_source.id,
            youtube_id=f"video_{i}",
            title=f"Video {i}",
            url=f"https://youtube.com/watch?v=video_{i}",
            duration_seconds=60 * (i + 1),
            status=status,
        )
        db_session.add(video)
        videos.append(video)

    db_session.commit()
    for video in videos:
        db_session.refresh(video)

    return videos
