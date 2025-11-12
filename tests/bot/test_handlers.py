"""
Tests para handlers del bot de Telegram.

Verifica que los comandos /start y /help funcionen correctamente.
"""

from unittest.mock import patch

import pytest

from src.bot.handlers.help import help_handler
from src.bot.handlers.start import start_handler


class TestStartHandler:
    """Tests para el handler del comando /start."""

    @pytest.mark.asyncio
    async def test_start_creates_new_user(self, mock_update, mock_context):
        """
        Verifica que /start crea un nuevo usuario en BD.

        Scenario: Usuario nuevo ejecuta /start por primera vez
        Expected: Usuario creado en BD + mensaje de bienvenida enviado
        """
        # Arrange
        first_name = mock_update.effective_user.first_name

        # Mock de la función de BD
        with patch("src.bot.handlers.start._create_or_update_user") as mock_create:
            mock_create.return_value = True  # Usuario nuevo creado

            # Act
            await start_handler(mock_update, mock_context)

            # Assert - Verificar que se llamó la función de BD
            mock_create.assert_called_once()

            # Assert - Verificar que se envió mensaje
            mock_update.message.reply_text.assert_called_once()
            message_sent = mock_update.message.reply_text.call_args[0][0]
            assert "Bienvenido" in message_sent
            assert first_name in message_sent
            assert "registrado correctamente" in message_sent

    @pytest.mark.asyncio
    async def test_start_with_existing_user_idempotent(self, mock_update, mock_context):
        """
        Verifica que /start es idempotente (no duplica usuario existente).

        Scenario: Usuario ejecuta /start dos veces
        Expected: Solo 1 registro en BD + mensaje "ya estabas registrado"
        """
        # Mock de la función de BD - usuario ya existe
        with patch("src.bot.handlers.start._create_or_update_user") as mock_create:
            mock_create.return_value = False  # Usuario ya existía

            # Act
            await start_handler(mock_update, mock_context)

            # Assert - Verificar mensaje de bienvenida
            mock_update.message.reply_text.assert_called_once()
            message_sent = mock_update.message.reply_text.call_args[0][0]
            assert "bienvenido de nuevo" in message_sent.lower()

    @pytest.mark.asyncio
    async def test_start_handles_user_without_username(self, mock_update, mock_context):
        """
        Verifica que /start maneja usuarios sin username.

        Scenario: Usuario de Telegram sin username configurado
        Expected: Usuario creado con username=None
        """
        # Arrange
        mock_update.effective_user.username = None

        # Mock de la función de BD
        with patch("src.bot.handlers.start._create_or_update_user") as mock_create:
            mock_create.return_value = True

            # Act
            await start_handler(mock_update, mock_context)

            # Assert - Verificar que se llamó con username=None
            call_args = mock_create.call_args[0]
            assert call_args[1] is None  # username es None
            assert call_args[2] is not None  # first_name no es None

    @pytest.mark.asyncio
    async def test_start_handles_database_error(self, mock_update, mock_context):
        """
        Verifica que /start maneja errores de BD correctamente.

        Scenario: Error al conectar con la base de datos
        Expected: Mensaje de error al usuario + error loggeado
        """
        # Arrange - Simular error de BD
        with patch("src.bot.handlers.start.SessionLocal") as mock_session:
            mock_session.side_effect = Exception("Database connection error")

            # Act
            await start_handler(mock_update, mock_context)

            # Assert - Verificar mensaje de error
            mock_update.message.reply_text.assert_called_once()
            message_sent = mock_update.message.reply_text.call_args[0][0]
            assert "error" in message_sent.lower()


class TestHelpHandler:
    """Tests para el handler del comando /help."""

    @pytest.mark.asyncio
    async def test_help_returns_command_list(self, mock_update, mock_context):
        """
        Verifica que /help devuelve la lista de comandos.

        Scenario: Usuario ejecuta /help
        Expected: Mensaje con todos los comandos disponibles
        """
        # Act
        await help_handler(mock_update, mock_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        message_sent = mock_update.message.reply_text.call_args[0][0]

        # Verificar que incluye comandos principales
        assert "/start" in message_sent
        assert "/help" in message_sent
        assert "/sources" in message_sent
        assert "/recent" in message_sent
        assert "/search" in message_sent

        # Verificar que tiene descripciones
        assert "Iniciar" in message_sent or "registrarse" in message_sent
        assert "comandos" in message_sent.lower()

    @pytest.mark.asyncio
    async def test_help_uses_markdown_formatting(self, mock_update, mock_context):
        """
        Verifica que /help usa formato Markdown.

        Scenario: Usuario ejecuta /help
        Expected: Mensaje formateado con Markdown (negritas, secciones)
        """
        # Act
        await help_handler(mock_update, mock_context)

        # Assert
        call_kwargs = mock_update.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "Markdown"
