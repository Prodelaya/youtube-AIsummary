"""
Fixtures compartidos para tests de repositories.

Este módulo proporciona fixtures reutilizables para tests de repositories,
incluyendo:
- Base de datos PostgreSQL en Docker (compatible con tipos JSONB, ARRAY)
- Sesiones de BD con rollback automático y cleanup
- Datos de ejemplo (sources, videos, transcriptions, summaries, users)

IMPORTANTE: Requiere PostgreSQL corriendo en Docker.
Ejecutar antes de los tests: docker-compose up -d postgres
"""

import pytest
import os
from datetime import datetime, UTC
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from src.models import Base, Source, Video, Transcription, Summary, TelegramUser, User
from src.models.video import VideoStatus


# ==================== CONFIGURACIÓN DE BD DE TESTS ====================

# URL de conexión a PostgreSQL de tests
# Usa una BD separada para tests para evitar conflictos
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://iamonitor:iamonitor_dev_password@localhost:5432/iamonitor_test"
)


# ==================== FIXTURES DE BASE DE DATOS ====================


@pytest.fixture(scope="session")
def db_engine_session():
    """
    Engine de PostgreSQL compartido para toda la sesión de tests.

    Scope 'session' significa que se crea UNA VEZ para todos los tests.
    Esto es más eficiente que crear un engine por cada test.

    Usa NullPool para evitar problemas de conexiones en tests paralelos.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,  # No usar pool en tests
        echo=False,  # Cambiar a True para debug SQL
    )

    # Crear todas las tablas
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup: eliminar todas las tablas al finalizar sesión
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_engine(db_engine_session):
    """
    Fixture que proporciona el engine a cada test.

    Simplemente retorna el engine de sesión, pero con scope 'function'
    para que cada test pueda usarlo independientemente.
    """
    return db_engine_session


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """
    Sesión de BD con rollback automático y limpieza de datos.

    Cada test obtiene una sesión limpia:
    1. Limpia todas las tablas antes del test
    2. Ejecuta el test
    3. Hace rollback y cierra la sesión

    Esto asegura aislamiento total entre tests.
    """
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()

    # Limpiar todas las tablas antes del test
    # Orden importante: eliminar primero tablas con FK
    try:
        session.execute(text("TRUNCATE TABLE summaries, transcriptions, videos, sources, telegram_users, users CASCADE"))
        session.commit()
    except Exception:
        session.rollback()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ==================== FIXTURES DE DATOS - SOURCES ====================


@pytest.fixture
def sample_source(db_session) -> Source:
    """
    Fuente de YouTube de ejemplo.

    Returns:
        Source activa con metadata básica.
    """
    source = Source(
        name="Test Channel",
        source_type="youtube",
        url="https://youtube.com/@testchannel",
        active=True
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def inactive_source(db_session) -> Source:
    """Fuente inactiva para tests de filtrado."""
    source = Source(
        name="Inactive Channel",
        source_type="youtube",
        url="https://youtube.com/@inactive",
        active=False
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def multiple_sources(db_session) -> list[Source]:
    """
    Lista de múltiples fuentes para tests de queries complejas.

    Returns:
        Lista de 5 sources (3 activas, 2 inactivas).
    """
    sources = [
        Source(
            name=f"Channel {i}",
            source_type="youtube",
            url=f"https://youtube.com/@channel{i}",
            active=(i % 3 != 0)  # Cada 3era está inactiva
        )
        for i in range(5)
    ]
    db_session.add_all(sources)
    db_session.commit()
    for source in sources:
        db_session.refresh(source)
    return sources


# ==================== FIXTURES DE DATOS - VIDEOS ====================


@pytest.fixture
def sample_video(db_session, sample_source) -> Video:
    """
    Video de ejemplo con metadata completa.

    Returns:
        Video en estado PENDING listo para procesar.
    """
    video = Video(
        url="https://youtube.com/watch?v=test123",
        youtube_id="test123",
        title="Test Video Title",
        duration_seconds=300,
        source_id=sample_source.id,
        status=VideoStatus.PENDING
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def completed_video(db_session, sample_source) -> Video:
    """Video completamente procesado."""
    video = Video(
        url="https://youtube.com/watch?v=completed",
        youtube_id="completed",
        title="Completed Video",
        duration_seconds=600,
        source_id=sample_source.id,
        status=VideoStatus.COMPLETED
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def failed_video(db_session, sample_source) -> Video:
    """Video que falló en procesamiento."""
    video = Video(
        url="https://youtube.com/watch?v=failed",
        youtube_id="failed",
        title="Failed Video",
        duration_seconds=200,
        source_id=sample_source.id,
        status=VideoStatus.FAILED
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def multiple_videos(db_session, sample_source) -> list[Video]:
    """
    Lista de múltiples videos en diferentes estados.

    Returns:
        Lista de 10 videos con estados variados.
    """
    statuses = [
        VideoStatus.PENDING,
        VideoStatus.DOWNLOADING,
        VideoStatus.COMPLETED,
        VideoStatus.FAILED,
        VideoStatus.PENDING,
        VideoStatus.COMPLETED,
        VideoStatus.COMPLETED,
        VideoStatus.PENDING,
        VideoStatus.SKIPPED,
        VideoStatus.FAILED
    ]

    videos = [
        Video(
            url=f"https://youtube.com/watch?v=video{i}",
            youtube_id=f"video{i}",
            title=f"Video {i}",
            duration_seconds=100 + (i * 50),
            source_id=sample_source.id,
            status=statuses[i]
        )
        for i in range(10)
    ]

    db_session.add_all(videos)
    db_session.commit()
    for video in videos:
        db_session.refresh(video)
    return videos


# ==================== FIXTURES DE DATOS - TRANSCRIPTIONS ====================


@pytest.fixture
def sample_transcription(db_session, sample_video) -> Transcription:
    """
    Transcripción de ejemplo.

    Returns:
        Transcripción en español asociada a sample_video.
    """
    transcription = Transcription(
        video_id=sample_video.id,
        text="Este es un texto de transcripción de prueba. Contiene información sobre testing en Python.",
        language="es",
        duration_seconds=300
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)
    return transcription


@pytest.fixture
def english_transcription(db_session, completed_video) -> Transcription:
    """Transcripción en inglés para tests de filtrado por idioma."""
    transcription = Transcription(
        video_id=completed_video.id,
        text="This is an English transcription for testing purposes.",
        language="en",
        duration_seconds=600
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)
    return transcription


# ==================== FIXTURES DE DATOS - SUMMARIES ====================


@pytest.fixture
def sample_summary(db_session, sample_transcription) -> Summary:
    """
    Resumen de ejemplo con keywords.

    Returns:
        Summary asociado a sample_transcription con keywords de Python/testing.
    """
    summary = Summary(
        transcription_id=sample_transcription.id,
        summary_text="Resumen de prueba del video sobre testing en Python. Se cubren conceptos de pytest y mocking.",
        keywords=["Python", "pytest", "testing", "mocking"]
    )
    db_session.add(summary)
    db_session.commit()
    db_session.refresh(summary)
    return summary


@pytest.fixture
def multiple_summaries(db_session, multiple_videos) -> list[Summary]:
    """
    Lista de múltiples resúmenes para tests de búsqueda.

    Returns:
        Lista de 5 summaries con diferentes keywords.
    """
    # Crear transcripciones primero
    transcriptions = []
    for i, video in enumerate(multiple_videos[:5]):
        trans = Transcription(
            video_id=video.id,
            text=f"Transcription {i}",
            language="es",
            duration_seconds=video.duration_seconds
        )
        db_session.add(trans)
        transcriptions.append(trans)

    db_session.commit()
    for trans in transcriptions:
        db_session.refresh(trans)

    # Crear resúmenes con diferentes temas
    summaries_data = [
        ("Resumen sobre FastAPI y desarrollo web", ["FastAPI", "Python", "Web", "API"]),
        ("Tutorial de Django para principiantes", ["Django", "Python", "Web"]),
        ("Machine Learning con TensorFlow", ["ML", "TensorFlow", "AI", "Python"]),
        ("Deployment con Docker y Kubernetes", ["Docker", "Kubernetes", "DevOps"]),
        ("Testing automatizado con pytest", ["pytest", "testing", "Python", "QA"])
    ]

    summaries = []
    for i, (text, keywords) in enumerate(summaries_data):
        summary = Summary(
            transcription_id=transcriptions[i].id,
            summary_text=text,
            keywords=keywords
        )
        db_session.add(summary)
        summaries.append(summary)

    db_session.commit()
    for summary in summaries:
        db_session.refresh(summary)
    return summaries


# ==================== FIXTURES DE DATOS - USERS ====================


@pytest.fixture
def sample_user(db_session) -> User:
    """
    Usuario admin de ejemplo.

    Returns:
        User con rol admin y password hasheado.
    """
    user = User(
        username="admin",
        email="admin@test.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU8KQDpTMWBq",  # "password123"
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session) -> User:
    """Usuario con rol normal (no admin)."""
    user = User(
        username="user",
        email="user@test.com",
        hashed_password="$2b$12$hashed_password",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_telegram_user(db_session) -> TelegramUser:
    """
    Usuario de Telegram de ejemplo.

    Returns:
        TelegramUser activo listo para recibir notificaciones.
    """
    user = TelegramUser(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        is_active=True,
        language_code="es"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_telegram_user(db_session) -> TelegramUser:
    """Usuario de Telegram inactivo (bot bloqueado)."""
    user = TelegramUser(
        telegram_id=987654321,
        username="inactive",
        is_active=False,
        bot_blocked=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def telegram_user_with_subscriptions(db_session, sample_source) -> TelegramUser:
    """Usuario de Telegram con suscripciones a fuentes."""
    user = TelegramUser(
        telegram_id=111222333,
        username="subscribed_user",
        is_active=True
    )
    user.subscribed_sources.append(sample_source)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
