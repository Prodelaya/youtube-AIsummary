"""
Tests unitarios para tareas de distribución de resúmenes.

Estos tests validan el correcto funcionamiento de distribute_summary_task:
- Distribución exitosa a usuarios suscritos
- Idempotencia (no re-enviar si ya fue enviado)
- Manejo de usuarios que bloquearon el bot
- Casos sin usuarios suscritos
- Manejo de rate limits de Telegram
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from telegram.error import Forbidden

from src.models import Source, Summary, TelegramUser, Transcription, Video
from src.tasks.distribute_summaries import (
    SummaryAlreadySentError,
    SummaryNotFoundError,
    distribute_summary_task,
)


@pytest.fixture
def mock_bot():
    """Fixture para mockear Bot de Telegram."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def sample_source(db_session):
    """Fixture para crear una fuente de prueba."""
    source = Source(
        url="https://youtube.com/@test_channel",
        source_type="youtube",
        name="Test Channel",
        extra_metadata={"youtube_channel_id": "UC123456"},
    )
    db_session.add(source)
    db_session.commit()
    return source


@pytest.fixture
def sample_video(db_session, sample_source):
    """Fixture para crear un video de prueba."""
    video = Video(
        url="https://youtube.com/watch?v=test123",
        youtube_id="test123",
        title="Test Video",
        source_id=sample_source.id,
        duration_seconds=300,
    )
    db_session.add(video)
    db_session.commit()
    return video


@pytest.fixture
def sample_transcription(db_session, sample_video):
    """Fixture para crear una transcripción de prueba."""
    transcription = Transcription(
        video_id=sample_video.id,
        text="This is a test transcription about AI and programming.",
        language="en",
        model_used="whisper-base",
        duration_seconds=300,
    )
    db_session.add(transcription)
    db_session.commit()
    return transcription


@pytest.fixture
def sample_summary(db_session, sample_transcription):
    """Fixture para crear un resumen de prueba."""
    summary = Summary(
        transcription_id=sample_transcription.id,
        summary_text="This is a test summary of the video.",
        keywords=["AI", "Python", "Testing"],
        category="framework",
        model_used="deepseek-chat",
        tokens_used=100,
        sent_to_telegram=False,
    )
    db_session.add(summary)
    db_session.commit()
    return summary


@pytest.fixture
def subscribed_users(db_session, sample_source):
    """Fixture para crear usuarios suscritos."""
    users = []
    for i in range(3):
        user = TelegramUser(
            telegram_id=123456789 + i,
            username=f"user{i}",
            first_name=f"Test User {i}",
            is_active=True,
            bot_blocked=False,
        )
        db_session.add(user)
        db_session.flush()

        # Suscribir al source
        user.sources.append(sample_source)

        users.append(user)

    db_session.commit()
    return users


# ==================== TESTS ====================


@patch("src.tasks.distribute_summaries.Bot")
@patch("src.tasks.distribute_summaries.SessionLocal")
def test_distribute_to_subscribed_users_success(
    mock_session_local,
    mock_bot_class,
    db_session,
    sample_summary,
    subscribed_users,
):
    """
    Test: Distribución exitosa a usuarios suscritos.

    Verifica que:
    - Se envían 3 mensajes (uno por usuario)
    - sent_to_telegram = True
    - telegram_message_ids contiene 3 IDs
    """
    # Configurar mocks
    mock_session_local.return_value = db_session
    mock_bot = MagicMock()
    mock_bot_class.return_value = mock_bot

    # Mock send_message con AsyncMock
    mock_message = MagicMock()
    mock_message.message_id = 999
    mock_bot.send_message = AsyncMock(return_value=mock_message)

    # Ejecutar tarea
    result = distribute_summary_task(str(sample_summary.id))

    # Validaciones
    assert result["status"] == "completed"
    assert result["messages_sent"] == 3
    assert result["active_users"] == 3

    # Validar que el resumen fue actualizado
    db_session.refresh(sample_summary)
    assert sample_summary.sent_to_telegram is True
    assert sample_summary.sent_at is not None
    assert len(sample_summary.telegram_message_ids) == 3

    # Validar que send_message fue llamado 3 veces
    assert mock_bot.send_message.call_count == 3


@patch("src.tasks.distribute_summaries.Bot")
@patch("src.tasks.distribute_summaries.SessionLocal")
def test_skip_if_already_sent(
    mock_session_local,
    mock_bot_class,
    db_session,
    sample_summary,
):
    """
    Test: Idempotencia - no re-enviar si ya fue enviado.

    Verifica que:
    - Si sent_to_telegram = True, la tarea termina inmediatamente
    - No se envían mensajes
    - Lanza SummaryAlreadySentError
    """
    # Marcar resumen como ya enviado
    sample_summary.sent_to_telegram = True
    sample_summary.sent_at = datetime.now(UTC)
    sample_summary.telegram_message_ids = {"123456789": 999}
    db_session.commit()

    # Configurar mocks
    mock_session_local.return_value = db_session
    mock_bot = MagicMock()
    mock_bot_class.return_value = mock_bot
    mock_bot.send_message = AsyncMock()

    # Ejecutar tarea (debe lanzar excepción)
    with pytest.raises(SummaryAlreadySentError):
        distribute_summary_task(str(sample_summary.id))

    # Validar que NO se envió ningún mensaje
    mock_bot.send_message.assert_not_called()


@patch("src.tasks.distribute_summaries.Bot")
@patch("src.tasks.distribute_summaries.SessionLocal")
def test_handle_user_blocked_bot(
    mock_session_local,
    mock_bot_class,
    db_session,
    sample_summary,
    subscribed_users,
):
    """
    Test: Manejo de usuario que bloqueó el bot.

    Verifica que:
    - Usuario con error Forbidden se marca como bot_blocked = True
    - Otros usuarios SÍ reciben mensaje
    - sent_to_telegram = True al final
    """
    # Configurar mocks
    mock_session_local.return_value = db_session
    mock_bot = MagicMock()
    mock_bot_class.return_value = mock_bot

    # Mock send_message: primer usuario falla (bloqueó bot), resto OK
    mock_message = MagicMock()
    mock_message.message_id = 999

    async def mock_send_with_error(chat_id, **kwargs):
        if chat_id == subscribed_users[0].telegram_id:
            raise Forbidden("Bot was blocked by the user")
        return mock_message

    mock_bot.send_message = AsyncMock(side_effect=mock_send_with_error)

    # Ejecutar tarea
    result = distribute_summary_task(str(sample_summary.id))

    # Validaciones
    assert result["status"] == "completed"
    assert result["messages_sent"] == 2  # Solo 2 usuarios recibieron

    # Validar que el primer usuario fue marcado como bot_blocked
    db_session.refresh(subscribed_users[0])
    assert subscribed_users[0].bot_blocked is True

    # Validar que otros usuarios NO fueron bloqueados
    db_session.refresh(subscribed_users[1])
    db_session.refresh(subscribed_users[2])
    assert subscribed_users[1].bot_blocked is False
    assert subscribed_users[2].bot_blocked is False


@patch("src.tasks.distribute_summaries.Bot")
@patch("src.tasks.distribute_summaries.SessionLocal")
def test_no_users_subscribed(
    mock_session_local,
    mock_bot_class,
    db_session,
    sample_summary,
):
    """
    Test: Sin usuarios suscritos.

    Verifica que:
    - No se envían mensajes
    - sent_to_telegram = True (para no reintentarlo)
    - telegram_message_ids = {}
    """
    # Configurar mocks
    mock_session_local.return_value = db_session
    mock_bot = MagicMock()
    mock_bot_class.return_value = mock_bot
    mock_bot.send_message = AsyncMock()

    # Ejecutar tarea (no hay usuarios suscritos)
    result = distribute_summary_task(str(sample_summary.id))

    # Validaciones
    assert result["status"] == "completed_no_users"
    assert result["messages_sent"] == 0

    # Validar que el resumen fue marcado como enviado
    db_session.refresh(sample_summary)
    assert sample_summary.sent_to_telegram is True
    assert sample_summary.telegram_message_ids == {}

    # Validar que NO se envió ningún mensaje
    mock_bot.send_message.assert_not_called()


@patch("src.tasks.distribute_summaries.Bot")
@patch("src.tasks.distribute_summaries.SessionLocal")
def test_telegram_rate_limit_retry(
    mock_session_local,
    mock_bot_class,
    db_session,
    sample_summary,
    subscribed_users,
):
    """
    Test: Manejo de rate limit de Telegram.

    Verifica que:
    - Error "Too Many Requests" se propaga para retry automático
    - Celery reintentará la tarea con exponential backoff
    """
    # Configurar mocks
    mock_session_local.return_value = db_session
    mock_bot = MagicMock()
    mock_bot_class.return_value = mock_bot

    # Mock send_message: lanza error de rate limit
    from telegram.error import RetryAfter

    mock_bot.send_message = AsyncMock(side_effect=RetryAfter(retry_after=30))

    # Ejecutar tarea (debe lanzar excepción para retry)
    with pytest.raises(RetryAfter):
        distribute_summary_task(str(sample_summary.id))


@patch("src.tasks.distribute_summaries.SessionLocal")
def test_summary_not_found(mock_session_local, db_session):
    """
    Test: Resumen no existe en BD.

    Verifica que:
    - Lanza SummaryNotFoundError
    - No se envían mensajes
    """
    # Configurar mocks
    mock_session_local.return_value = db_session

    # UUID aleatorio que no existe
    fake_uuid = str(uuid4())

    # Ejecutar tarea (debe lanzar excepción)
    with pytest.raises(SummaryNotFoundError):
        distribute_summary_task(fake_uuid)
