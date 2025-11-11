"""
Fixtures compartidos para tests de repositories.

Este módulo proporciona fixtures de pytest para tests de integración
que usan la base de datos real con transacciones y rollback automático.
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings
from src.models import Source, Summary, TelegramUser, Transcription, Video, VideoStatus
from src.models.base import Base

# Engine de test (reutiliza la misma BD pero con transacciones aisladas)
test_engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    echo=False,  # Silenciar logs SQL en tests
)


@pytest.fixture(scope="function")
def db_session():
    """
    Fixture que proporciona una sesión de BD con rollback automático.

    Cada test se ejecuta en una transacción que se revierte al finalizar,
    garantizando que los tests no ensucien la base de datos.

    Uso:
        def test_create_source(db_session):
            source = Source(name="Test", url="https://test.com")
            db_session.add(source)
            db_session.commit()
            # Al finalizar el test, todo se revierte automáticamente

    Yields:
        Session: Sesión de SQLAlchemy con rollback automático
    """
    # Crear conexión y transacción
    connection = test_engine.connect()
    transaction = connection.begin()

    # Crear sesión ligada a la transacción
    TestSessionLocal = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
    )
    session = TestSessionLocal()

    # Asegurar que las tablas existen
    Base.metadata.create_all(bind=test_engine)

    yield session

    # Cleanup: cerrar sesión y revertir transacción
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_source(db_session) -> Source:
    """
    Factory fixture que crea una Source de prueba en la BD.

    Retorna una Source ya persistida en la base de datos,
    lista para ser usada en tests.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)

    Returns:
        Source: Instancia persistida en BD

    Uso:
        def test_something(sample_source):
            assert sample_source.id is not None
            assert sample_source.name == "Test Channel"
    """
    source = Source(
        name="Test Channel",
        url="https://youtube.com/@TestChannel",
        source_type="youtube",
        active=True,
        extra_metadata={"subscriber_count": 1000, "language": "en"},
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def inactive_source(db_session) -> Source:
    """
    Factory fixture que crea una Source inactiva de prueba.

    Útil para tests que validan filtrado por active=True/False.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)

    Returns:
        Source: Instancia inactiva persistida en BD
    """
    source = Source(
        name="Inactive Channel",
        url="https://youtube.com/@InactiveChannel",
        source_type="youtube",
        active=False,
        extra_metadata={},
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def source_factory(db_session):
    """
    Factory fixture avanzado que permite crear Sources con parámetros custom.

    Retorna una función que crea Sources, permitiendo personalización
    completa de atributos en cada test.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)

    Returns:
        callable: Función que crea Sources personalizadas

    Uso:
        def test_multiple_sources(source_factory):
            source1 = source_factory(name="Channel 1", url="https://ch1.com")
            source2 = source_factory(name="Channel 2", url="https://ch2.com", active=False)
    """

    def _create_source(
        name: str = "Default Channel",
        url: str = "https://youtube.com/@default",
        source_type: str = "youtube",
        active: bool = True,
        extra_metadata: dict | None = None,
    ) -> Source:
        source = Source(
            name=name,
            url=url,
            source_type=source_type,
            active=active,
            extra_metadata=extra_metadata or {},
        )
        db_session.add(source)
        db_session.commit()
        db_session.refresh(source)
        return source

    return _create_source


# ==================== VIDEO FIXTURES ====================


@pytest.fixture
def sample_video(db_session, sample_source) -> Video:
    """
    Factory fixture que crea un Video de prueba en la BD.

    Retorna un Video ya persistido, vinculado a sample_source,
    listo para ser usado en tests.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)
        sample_source: Source de prueba (inyectada automáticamente)

    Returns:
        Video: Instancia persistida en BD con status PENDING

    Uso:
        def test_something(sample_video):
            assert sample_video.id is not None
            assert sample_video.status == VideoStatus.PENDING
    """
    video = Video(
        source_id=sample_source.id,
        youtube_id="test_video_123",
        title="Test Video",
        url="https://youtube.com/watch?v=test123",
        duration_seconds=600,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
        extra_metadata={"view_count": 1000, "like_count": 50},
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def video_factory(db_session):
    """
    Factory fixture avanzado que permite crear Videos con parámetros custom.

    Retorna una función que crea Videos, permitiendo personalización
    completa de atributos en cada test.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)

    Returns:
        callable: Función que crea Videos personalizados

    Uso:
        def test_multiple_videos(sample_source, video_factory):
            video1 = video_factory(
                source_id=sample_source.id,
                youtube_id="abc123",
                title="Video 1",
                status=VideoStatus.PENDING
            )
            video2 = video_factory(
                source_id=sample_source.id,
                youtube_id="xyz789",
                title="Video 2",
                status=VideoStatus.COMPLETED
            )
    """

    def _create_video(
        source_id: UUID,
        youtube_id: str = "default_yt_id",
        title: str = "Default Video Title",
        url: str = "https://youtube.com/watch?v=default",
        duration_seconds: int | None = 300,
        status: VideoStatus = VideoStatus.PENDING,
        published_at: datetime | None = None,
        extra_metadata: dict | None = None,
    ) -> Video:
        video = Video(
            source_id=source_id,
            youtube_id=youtube_id,
            title=title,
            url=url,
            duration_seconds=duration_seconds,
            status=status,
            published_at=published_at or datetime.now(timezone.utc),
            extra_metadata=extra_metadata or {},
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)
        return video

    return _create_video


# ==================== TRANSCRIPTION FIXTURES ====================


@pytest.fixture
def sample_transcription(db_session, sample_video) -> Transcription:
    """
    Factory fixture que crea una Transcription de prueba en la BD.

    Retorna una Transcription ya persistida, vinculada a sample_video,
    lista para ser usada en tests.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)
        sample_video: Video de prueba (inyectado automáticamente)

    Returns:
        Transcription: Instancia persistida en BD con idioma "en"

    Uso:
        def test_something(sample_transcription):
            assert sample_transcription.id is not None
            assert sample_transcription.video_id == sample_video.id
            assert sample_transcription.language == "en"
    """
    transcription = Transcription(
        video_id=sample_video.id,
        text="This is a test transcription of the video content. "
        "It contains multiple sentences to simulate real transcriptions.",
        language="en",
        model_used="whisper-base",
        duration_seconds=600,
        confidence_score=0.92,
        segments=None,  # Sin segmentos por defecto
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)
    return transcription


@pytest.fixture
def transcription_factory(db_session):
    """
    Factory fixture avanzado que permite crear Transcriptions con parámetros custom.

    Retorna una función que crea Transcriptions, permitiendo personalización
    completa de atributos en cada test.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)

    Returns:
        callable: Función que crea Transcriptions personalizadas

    Uso:
        def test_multiple_transcriptions(sample_video, transcription_factory):
            trans1 = transcription_factory(
                video_id=sample_video.id,
                language="es",
                text="Transcripción en español"
            )
            trans2 = transcription_factory(
                video_id=another_video.id,
                language="en",
                text="English transcription",
                segments={"segments": [...]}
            )
    """

    def _create_transcription(
        video_id: UUID,
        text: str = "Default transcription text for testing purposes.",
        language: str = "en",
        model_used: str = "whisper-base",
        duration_seconds: int | None = 300,
        confidence_score: float | None = 0.85,
        segments: dict | None = None,
    ) -> Transcription:
        transcription = Transcription(
            video_id=video_id,
            text=text,
            language=language,
            model_used=model_used,
            duration_seconds=duration_seconds,
            confidence_score=confidence_score,
            segments=segments,
        )
        db_session.add(transcription)
        db_session.commit()
        db_session.refresh(transcription)
        return transcription

    return _create_transcription


# ==================== SUMMARY FIXTURES ====================


@pytest.fixture
def sample_summary(db_session, sample_transcription) -> Summary:
    """
    Factory fixture que crea un Summary de prueba en la BD.

    Retorna un Summary ya persistido, vinculado a sample_transcription,
    listo para ser usado en tests.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)
        sample_transcription: Transcription de prueba (inyectada automáticamente)

    Returns:
        Summary: Instancia persistida en BD con category="framework"

    Uso:
        def test_something(sample_summary):
            assert sample_summary.id is not None
            assert sample_summary.transcription_id == sample_transcription.id
            assert sample_summary.category == "framework"
    """
    summary = Summary(
        transcription_id=sample_transcription.id,
        summary_text="Este es un resumen de prueba sobre FastAPI. "
        "FastAPI es un framework web moderno para Python que permite "
        "crear APIs de forma rápida y eficiente usando async/await.",
        keywords=["fastapi", "python", "async", "web", "api"],
        category="framework",
        model_used="deepseek-chat",
        tokens_used=850,
        input_tokens=700,
        output_tokens=150,
        processing_time_ms=1200,
        extra_metadata={"temperature": 0.7, "max_tokens": 500},
        sent_to_telegram=False,
        sent_at=None,
        telegram_message_ids=None,
    )
    db_session.add(summary)
    db_session.commit()
    db_session.refresh(summary)
    return summary


@pytest.fixture
def summary_factory(db_session):
    """
    Factory fixture avanzado que permite crear Summaries con parámetros custom.

    Retorna una función que crea Summaries, permitiendo personalización
    completa de atributos en cada test.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)

    Returns:
        callable: Función que crea Summaries personalizados

    Uso:
        def test_multiple_summaries(sample_transcription, summary_factory):
            sum1 = summary_factory(
                transcription_id=sample_transcription.id,
                summary_text="Resumen sobre Docker",
                category="tool",
                keywords=["docker", "containers"]
            )
            sum2 = summary_factory(
                transcription_id=another_transcription.id,
                summary_text="Resumen sobre Python",
                category="language",
                keywords=["python", "programming"]
            )
    """

    _UNSET = object()  # Sentinel value para distinguir None de "no pasado"

    def _create_summary(
        transcription_id: UUID,
        summary_text: str = "Default summary text for testing purposes.",
        keywords=_UNSET,
        category: str | None = "concept",
        model_used: str = "deepseek-chat",
        tokens_used: int | None = 500,
        input_tokens: int | None = 400,
        output_tokens: int | None = 100,
        processing_time_ms: int | None = 800,
        extra_metadata=_UNSET,
    ) -> Summary:
        # Manejar defaults vs None explícito
        if keywords is _UNSET:
            keywords_value = ["test", "default"]
        else:
            keywords_value = keywords

        if extra_metadata is _UNSET:
            extra_metadata_value = {}
        else:
            extra_metadata_value = extra_metadata

        summary = Summary(
            transcription_id=transcription_id,
            summary_text=summary_text,
            keywords=keywords_value,
            category=category,
            model_used=model_used,
            tokens_used=tokens_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            processing_time_ms=processing_time_ms,
            extra_metadata=extra_metadata_value,
            sent_to_telegram=False,  # Por defecto no enviado
            sent_at=None,
            telegram_message_ids=None,
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        return summary

    return _create_summary


# ==================== TELEGRAM USER FIXTURES ====================


@pytest.fixture
def sample_telegram_user(db_session) -> TelegramUser:
    """
    Factory fixture que crea un TelegramUser de prueba en la BD.

    Retorna un TelegramUser ya persistido, listo para ser usado en tests.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)

    Returns:
        TelegramUser: Instancia persistida en BD

    Uso:
        def test_something(sample_telegram_user):
            assert sample_telegram_user.id is not None
            assert sample_telegram_user.telegram_id == 123456789
            assert sample_telegram_user.username == "test_user"
    """
    user = TelegramUser(
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User",
        is_active=True,
        language_code="es",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def telegram_user_factory(db_session):
    """
    Factory fixture avanzado que permite crear TelegramUsers con parámetros custom.

    Retorna una función que crea TelegramUsers, permitiendo personalización
    completa de atributos en cada test.

    Args:
        db_session: Sesión de BD (inyectada automáticamente)

    Returns:
        callable: Función que crea TelegramUsers personalizados

    Uso:
        def test_multiple_users(telegram_user_factory):
            user1 = telegram_user_factory(
                telegram_id=111111111,
                username="user1",
                first_name="John"
            )
            user2 = telegram_user_factory(
                telegram_id=222222222,
                username="user2",
                first_name="Jane"
            )
    """

    def _create_telegram_user(
        telegram_id: int = 999999999,
        username: str | None = "default_user",
        first_name: str | None = "Default",
        last_name: str | None = "User",
        is_active: bool = True,
        language_code: str | None = "es",
    ) -> TelegramUser:
        user = TelegramUser(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            language_code=language_code,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_telegram_user
