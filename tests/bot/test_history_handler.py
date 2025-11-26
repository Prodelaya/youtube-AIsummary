"""
Tests para el handler del comando /recent y callback view_transcript.

Verifica que los usuarios puedan ver sus últimos resúmenes y
acceder a transcripciones completas.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from telegram import CallbackQuery

from src.bot.handlers.history import (
    recent_handler,
    view_transcript_callback,
)


@pytest.fixture
def mock_callback_query(mock_telegram_user, mock_message):
    """
    Fixture que crea un CallbackQuery mock para botones inline.

    Returns:
        CallbackQuery mock con métodos async
    """
    query = MagicMock(spec=CallbackQuery)
    query.from_user = mock_telegram_user
    query.message = mock_message
    query.data = None  # Se configurará en cada test
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_update_with_callback(mock_update, mock_telegram_user, mock_callback_query):
    """
    Fixture que crea un Update con callback_query.

    Returns:
        Update mock con callback_query configurado
    """
    mock_update.callback_query = mock_callback_query
    mock_update.effective_user = mock_telegram_user
    return mock_update


@pytest.fixture
def mock_summaries_data():
    """
    Fixture que simula lista de resúmenes con relaciones.

    Returns:
        Lista de dicts con summary, video, source
    """
    summaries = []

    for i in range(3):
        # Mock Source
        source = MagicMock()
        source.id = uuid4()
        source.name = f"TestChannel{i + 1}"
        source.url = f"https://youtube.com/@test{i + 1}"

        # Mock Video
        video = MagicMock()
        video.id = uuid4()
        video.youtube_id = f"test_video_{i}"
        video.title = f"Test Video {i + 1}"
        video.url = f"https://youtube.com/watch?v=test{i}"
        video.duration_seconds = 600 + (i * 100)
        video.extra_metadata = {"view_count": 10000 * (i + 1)}
        video.published_at = None

        # Mock Summary
        summary = MagicMock()
        summary.id = uuid4()
        summary.summary_text = f"This is a test summary number {i + 1}. " * 10
        summary.keywords = [f"keyword{i + 1}", "test", "python"]
        summary.category = "tutorial"

        summaries.append({"summary": summary, "video": video, "source": source})

    return summaries


class TestRecentHandler:
    """Tests para el handler del comando /recent."""

    @pytest.mark.asyncio
    async def test_recent_command_with_summaries(
        self, mock_update, mock_context, mock_summaries_data
    ):
        """
        Verifica que /recent muestra resúmenes cuando existen.

        Scenario: Usuario con suscripciones ejecuta /recent
        Expected: Lista de resúmenes con botones inline mostrada
        """
        with patch(
            "src.bot.handlers.history._get_user_recent_summaries",
            return_value=mock_summaries_data,
        ):
            await recent_handler(mock_update, mock_context)

            # Verificar que se envió header
            assert mock_update.message.reply_text.call_count == 4  # Header + 3 summaries

            # Verificar que el header contiene el count correcto
            first_call = mock_update.message.reply_text.call_args_list[0]
            assert "3" in str(first_call)  # Debe mencionar 3 resúmenes

            # Verificar que cada resumen se envió con keyboard
            for i in range(1, 4):  # Llamadas 2, 3, 4 son los resúmenes
                call = mock_update.message.reply_text.call_args_list[i]
                # Verificar que hay reply_markup (botón inline)
                assert "reply_markup" in call.kwargs or len(call.args) > 1

    @pytest.mark.asyncio
    async def test_recent_command_no_summaries(self, mock_update, mock_context):
        """
        Verifica mensaje cuando usuario no tiene resúmenes.

        Scenario: Usuario sin suscripciones o sin resúmenes ejecuta /recent
        Expected: Mensaje informativo mostrado
        """
        with patch("src.bot.handlers.history._get_user_recent_summaries", return_value=[]):
            await recent_handler(mock_update, mock_context)

            # Verificar que se envió solo 1 mensaje (el informativo)
            assert mock_update.message.reply_text.call_count == 1

            # Verificar contenido del mensaje
            call_args = mock_update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")
            assert "No tienes resúmenes recientes" in message_text
            assert "/sources" in message_text

    @pytest.mark.asyncio
    async def test_recent_command_without_user(self, mock_update, mock_context):
        """
        Verifica que handler maneja gracefully ausencia de effective_user.

        Scenario: Update sin effective_user (edge case)
        Expected: Handler retorna sin error
        """
        mock_update.effective_user = None

        await recent_handler(mock_update, mock_context)

        # No debe haber llamadas a reply_text
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_recent_command_handles_exception(self, mock_update, mock_context):
        """
        Verifica manejo de errores en /recent.

        Scenario: Error de BD al obtener resúmenes
        Expected: Mensaje de error amigable enviado
        """
        with patch(
            "src.bot.handlers.history._get_user_recent_summaries",
            side_effect=Exception("Database error"),
        ):
            await recent_handler(mock_update, mock_context)

            # Verificar que se envió mensaje de error
            assert mock_update.message.reply_text.call_count == 1
            call_args = mock_update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")
            assert "error" in message_text.lower()


class TestViewTranscriptCallback:
    """Tests para el callback handler view_transcript."""

    @pytest.mark.asyncio
    async def test_view_transcript_callback_success(self, mock_update_with_callback, mock_context):
        """
        Verifica que callback muestra transcripción correctamente.

        Scenario: Usuario hace click en "Ver transcripción"
        Expected: Transcripción enviada al usuario
        """
        summary_id = uuid4()
        mock_update_with_callback.callback_query.data = f"view_transcript:{summary_id}"

        transcription_text = "This is a test transcription. " * 20

        with patch(
            "src.bot.handlers.history._get_transcription_by_summary_id",
            return_value=transcription_text,
        ):
            # Mock del context.bot.send_message
            mock_context.bot.send_message = AsyncMock()

            await view_transcript_callback(mock_update_with_callback, mock_context)

            # Verificar que se respondió al callback
            mock_update_with_callback.callback_query.answer.assert_called_once()

            # Verificar que se envió la transcripción
            mock_context.bot.send_message.assert_called_once()

            # Verificar que el mensaje contiene la transcripción
            call_args = mock_context.bot.send_message.call_args
            assert transcription_text in str(call_args)

    @pytest.mark.asyncio
    async def test_view_transcript_callback_not_found(
        self, mock_update_with_callback, mock_context
    ):
        """
        Verifica manejo cuando transcripción no existe.

        Scenario: Usuario hace click en transcripción eliminada
        Expected: Mensaje de error mostrado
        """
        summary_id = uuid4()
        mock_update_with_callback.callback_query.data = f"view_transcript:{summary_id}"

        with patch(
            "src.bot.handlers.history._get_transcription_by_summary_id",
            return_value=None,
        ):
            await view_transcript_callback(mock_update_with_callback, mock_context)

            # Verificar que se respondió con error
            mock_update_with_callback.callback_query.answer.assert_called_once()
            call_args = mock_update_with_callback.callback_query.answer.call_args
            assert "no encontrada" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_view_transcript_callback_invalid_format(
        self, mock_update_with_callback, mock_context
    ):
        """
        Verifica manejo de callback_data malformado.

        Scenario: Callback con formato inválido
        Expected: Mensaje de error mostrado
        """
        mock_update_with_callback.callback_query.data = "view_transcript:invalid-uuid"

        await view_transcript_callback(mock_update_with_callback, mock_context)

        # Verificar que se respondió con error
        mock_update_with_callback.callback_query.answer.assert_called_once()
        call_args = mock_update_with_callback.callback_query.answer.call_args
        assert "error" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_view_transcript_callback_handles_exception(
        self, mock_update_with_callback, mock_context
    ):
        """
        Verifica manejo de errores en callback.

        Scenario: Error de BD al obtener transcripción
        Expected: Mensaje de error amigable enviado
        """
        summary_id = uuid4()
        mock_update_with_callback.callback_query.data = f"view_transcript:{summary_id}"

        with patch(
            "src.bot.handlers.history._get_transcription_by_summary_id",
            side_effect=Exception("Database error"),
        ):
            await view_transcript_callback(mock_update_with_callback, mock_context)

            # Verificar que se respondió con error
            mock_update_with_callback.callback_query.answer.assert_called_once()
            call_args = mock_update_with_callback.callback_query.answer.call_args
            assert "error" in str(call_args).lower()
