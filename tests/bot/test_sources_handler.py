"""
Tests para el handler del comando /sources y callback de suscripciones.

Verifica que los usuarios puedan ver canales, suscribirse y desuscribirse.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from telegram import CallbackQuery, InlineKeyboardMarkup

from src.bot.handlers.sources import sources_handler, toggle_subscription_callback


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
    query.edit_message_reply_markup = AsyncMock()
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
def mock_sources_data():
    """
    Fixture que simula lista de fuentes de BD.

    Returns:
        Lista de tuplas (source_dict, is_subscribed)
    """
    source1_id = uuid4()
    source2_id = uuid4()
    source3_id = uuid4()

    return [
        (
            {
                "id": source1_id,
                "name": "Fireship",
                "url": "https://youtube.com/@fireship",
                "source_type": "youtube",
            },
            False,
        ),
        (
            {
                "id": source2_id,
                "name": "ThePrimeagen",
                "url": "https://youtube.com/@theprimeagen",
                "source_type": "youtube",
            },
            True,
        ),
        (
            {
                "id": source3_id,
                "name": "Midudev",
                "url": "https://youtube.com/@midudev",
                "source_type": "youtube",
            },
            False,
        ),
    ]


class TestSourcesHandler:
    """Tests para el handler del comando /sources."""

    @pytest.mark.asyncio
    async def test_sources_command_shows_channels_list(
        self, mock_update, mock_context, mock_sources_data
    ):
        """
        Verifica que /sources muestra lista de canales disponibles.

        Scenario: Usuario ejecuta /sources con canales disponibles
        Expected: Lista de canales con teclado inline mostrado
        """
        # Arrange
        with patch(
            "src.bot.handlers.sources._get_sources_with_subscription_status"
        ) as mock_get_sources:
            mock_get_sources.return_value = mock_sources_data

            # Act
            await sources_handler(mock_update, mock_context)

            # Assert - Verificar que se llamó a la función de BD
            mock_get_sources.assert_called_once()

            # Assert - Verificar que se envió mensaje con teclado
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args

            message_sent = call_args[0][0]
            assert "CANALES DISPONIBLES" in message_sent
            assert "Fireship" not in message_sent  # Los canales están en botones, no en texto
            assert "suscripciones activas" in message_sent.lower()

            # Verificar que se envió teclado inline
            call_kwargs = call_args[1]
            assert "reply_markup" in call_kwargs
            assert isinstance(call_kwargs["reply_markup"], InlineKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_sources_command_reflects_user_subscriptions(
        self, mock_update, mock_context, mock_sources_data
    ):
        """
        Verifica que /sources muestra correctamente el estado de suscripciones.

        Scenario: Usuario con 1 suscripción de 3 canales totales
        Expected: Contador muestra "1/3" y botones tienen ✅/❌ correctos
        """
        # Arrange - Mock data: 1 canal suscrito de 3
        with patch(
            "src.bot.handlers.sources._get_sources_with_subscription_status"
        ) as mock_get_sources:
            mock_get_sources.return_value = mock_sources_data

            # Act
            await sources_handler(mock_update, mock_context)

            # Assert - Verificar contador de suscripciones
            message_sent = mock_update.message.reply_text.call_args[0][0]
            assert "1/3" in message_sent  # 1 suscripción de 3 canales

            # Verificar que se generó teclado con botones correctos
            keyboard = mock_update.message.reply_text.call_args[1]["reply_markup"]
            buttons = keyboard.inline_keyboard

            # Verificar cantidad de botones
            assert len(buttons) == 3  # 3 canales = 3 filas

            # Verificar texto de botones (deben incluir ✅ o ❌)
            button_texts = [row[0].text for row in buttons]
            assert any("❌" in text and "Fireship" in text for text in button_texts)
            assert any("✅" in text and "ThePrimeagen" in text for text in button_texts)
            assert any("❌" in text and "Midudev" in text for text in button_texts)

    @pytest.mark.asyncio
    async def test_sources_command_with_no_channels(self, mock_update, mock_context):
        """
        Verifica que /sources maneja correctamente el caso sin canales.

        Scenario: BD sin canales activos
        Expected: Mensaje informativo al usuario
        """
        # Arrange - Mock sin canales
        with patch(
            "src.bot.handlers.sources._get_sources_with_subscription_status"
        ) as mock_get_sources:
            mock_get_sources.return_value = []

            # Act
            await sources_handler(mock_update, mock_context)

            # Assert - Verificar mensaje apropiado
            mock_update.message.reply_text.assert_called_once()
            message_sent = mock_update.message.reply_text.call_args[0][0]
            assert "no hay canales" in message_sent.lower()
            assert "disponibles" in message_sent.lower()

            # Verificar que NO se envió teclado
            call_kwargs = mock_update.message.reply_text.call_args[1]
            assert "reply_markup" not in call_kwargs or call_kwargs.get("reply_markup") is None

    @pytest.mark.asyncio
    async def test_sources_command_handles_database_error(self, mock_update, mock_context):
        """
        Verifica que /sources maneja errores de BD correctamente.

        Scenario: Error al consultar canales desde BD
        Expected: Mensaje de error al usuario + error loggeado
        """
        # Arrange - Simular error de BD
        with patch(
            "src.bot.handlers.sources._get_sources_with_subscription_status"
        ) as mock_get_sources:
            mock_get_sources.side_effect = Exception("Database connection error")

            # Act
            await sources_handler(mock_update, mock_context)

            # Assert - Verificar mensaje de error
            mock_update.message.reply_text.assert_called_once()
            message_sent = mock_update.message.reply_text.call_args[0][0]
            assert "error" in message_sent.lower()


class TestToggleSubscriptionCallback:
    """Tests para el callback handler de toggle de suscripciones."""

    @pytest.mark.asyncio
    async def test_toggle_subscribe_to_channel(
        self, mock_update_with_callback, mock_context, mock_sources_data
    ):
        """
        Verifica que click en canal no suscrito lo suscribe.

        Scenario: Usuario hace click en [❌ Fireship]
        Expected: Suscripción creada + teclado actualizado + feedback ✅
        """
        # Arrange
        source_id = mock_sources_data[0][0]["id"]
        source_name = mock_sources_data[0][0]["name"]
        mock_update_with_callback.callback_query.data = f"toggle_source:{source_id}"

        with (
            patch("src.bot.handlers.sources._toggle_user_subscription") as mock_toggle,
            patch(
                "src.bot.handlers.sources._get_sources_with_subscription_status"
            ) as mock_get_sources,
        ):
            mock_toggle.return_value = {"action": "subscribed", "source_name": source_name}
            # Simular estado después del toggle (ahora suscrito)
            updated_sources = mock_sources_data.copy()
            updated_sources[0] = (updated_sources[0][0], True)
            mock_get_sources.return_value = updated_sources

            # Act
            await toggle_subscription_callback(mock_update_with_callback, mock_context)

            # Assert - Verificar que se llamó a toggle
            mock_toggle.assert_called_once()

            # Assert - Verificar que se actualizó mensaje con teclado
            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

            # Assert - Verificar feedback al usuario
            mock_update_with_callback.callback_query.answer.assert_called_once()
            feedback = mock_update_with_callback.callback_query.answer.call_args[0][0]
            assert "✅" in feedback
            assert "Suscrito" in feedback
            assert source_name in feedback

    @pytest.mark.asyncio
    async def test_toggle_unsubscribe_from_channel(
        self, mock_update_with_callback, mock_context, mock_sources_data
    ):
        """
        Verifica que click en canal suscrito lo desuscribe.

        Scenario: Usuario hace click en [✅ ThePrimeagen]
        Expected: Suscripción eliminada + teclado actualizado + feedback ❌
        """
        # Arrange
        source_id = mock_sources_data[1][0]["id"]
        source_name = mock_sources_data[1][0]["name"]
        mock_update_with_callback.callback_query.data = f"toggle_source:{source_id}"

        with (
            patch("src.bot.handlers.sources._toggle_user_subscription") as mock_toggle,
            patch(
                "src.bot.handlers.sources._get_sources_with_subscription_status"
            ) as mock_get_sources,
        ):
            mock_toggle.return_value = {"action": "unsubscribed", "source_name": source_name}
            # Simular estado después del toggle (ahora desuscrito)
            updated_sources = mock_sources_data.copy()
            updated_sources[1] = (updated_sources[1][0], False)
            mock_get_sources.return_value = updated_sources

            # Act
            await toggle_subscription_callback(mock_update_with_callback, mock_context)

            # Assert - Verificar que se llamó a toggle
            mock_toggle.assert_called_once()

            # Assert - Verificar feedback al usuario
            feedback = mock_update_with_callback.callback_query.answer.call_args[0][0]
            assert "❌" in feedback
            assert "Desuscrito" in feedback
            assert source_name in feedback

    @pytest.mark.asyncio
    async def test_callback_query_with_invalid_callback_data(
        self, mock_update_with_callback, mock_context
    ):
        """
        Verifica manejo de callback_data inválido.

        Scenario: callback_data malformado o UUID inválido
        Expected: Error enviado al usuario sin crashear
        """
        # Arrange - callback_data inválido
        mock_update_with_callback.callback_query.data = "toggle_source:INVALID_UUID"

        # Act
        await toggle_subscription_callback(mock_update_with_callback, mock_context)

        # Assert - Verificar que se envió mensaje de error
        mock_update_with_callback.callback_query.answer.assert_called_once()
        feedback = mock_update_with_callback.callback_query.answer.call_args[0][0]
        assert "❌" in feedback or "Error" in feedback

    @pytest.mark.asyncio
    async def test_callback_query_handles_not_found_error(
        self, mock_update_with_callback, mock_context
    ):
        """
        Verifica manejo de canal no encontrado.

        Scenario: Usuario intenta toggle en canal que fue eliminado
        Expected: Mensaje de error apropiado
        """
        # Arrange
        source_id = uuid4()
        mock_update_with_callback.callback_query.data = f"toggle_source:{source_id}"

        with patch("src.bot.handlers.sources._toggle_user_subscription") as mock_toggle:
            from src.repositories.exceptions import NotFoundError

            mock_toggle.side_effect = NotFoundError("Source", source_id)

            # Act
            await toggle_subscription_callback(mock_update_with_callback, mock_context)

            # Assert - Verificar mensaje de error
            mock_update_with_callback.callback_query.answer.assert_called_once()
            feedback = mock_update_with_callback.callback_query.answer.call_args[0][0]
            assert "no encontrado" in feedback.lower() or "Canal no encontrado" in feedback

    @pytest.mark.asyncio
    async def test_callback_query_handles_database_error(
        self, mock_update_with_callback, mock_context
    ):
        """
        Verifica manejo de errores de BD durante toggle.

        Scenario: Error de conexión a BD durante toggle
        Expected: Mensaje de error genérico + error loggeado
        """
        # Arrange
        source_id = uuid4()
        mock_update_with_callback.callback_query.data = f"toggle_source:{source_id}"

        with patch("src.bot.handlers.sources._toggle_user_subscription") as mock_toggle:
            mock_toggle.side_effect = Exception("Database connection error")

            # Act
            await toggle_subscription_callback(mock_update_with_callback, mock_context)

            # Assert - Verificar mensaje de error
            mock_update_with_callback.callback_query.answer.assert_called_once()
            feedback = mock_update_with_callback.callback_query.answer.call_args[0][0]
            assert "❌" in feedback or "error" in feedback.lower()
