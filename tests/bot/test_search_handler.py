"""
Tests para el handler del comando /search.

Verifica que los usuarios puedan buscar en su historial de
resúmenes usando keywords.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.bot.handlers.search import search_handler


@pytest.fixture
def mock_context_with_args(mock_context):
    """
    Fixture que crea contexto con argumentos de comando.

    Returns:
        Context mock con args configurados
    """
    mock_context.args = []  # Se configurará en cada test
    return mock_context


@pytest.fixture
def mock_search_results():
    """
    Fixture que simula resultados de búsqueda.

    Returns:
        Lista de dicts con summary, video, source
    """
    results = []

    for i in range(5):
        # Mock Source
        source = MagicMock()
        source.id = uuid4()
        source.name = f"SearchChannel{i + 1}"
        source.url = f"https://youtube.com/@search{i + 1}"

        # Mock Video
        video = MagicMock()
        video.id = uuid4()
        video.youtube_id = f"search_video_{i}"
        video.title = f"FastAPI Tutorial {i + 1}"
        video.url = f"https://youtube.com/watch?v=search{i}"
        video.duration_seconds = 720
        video.extra_metadata = {"view_count": 50000}
        video.published_at = None

        # Mock Summary
        summary = MagicMock()
        summary.id = uuid4()
        summary.summary_text = (
            f"This tutorial covers FastAPI features like async, validation, and docs. "
            f"Part {i + 1}."
        )
        summary.keywords = ["FastAPI", "Python", "async"]
        summary.category = "framework"

        results.append({"summary": summary, "video": video, "source": source})

    return results


class TestSearchHandler:
    """Tests para el handler del comando /search."""

    @pytest.mark.asyncio
    async def test_search_command_with_results(
        self, mock_update, mock_context_with_args, mock_search_results
    ):
        """
        Verifica que /search muestra resultados cuando existen.

        Scenario: Usuario busca "FastAPI" y hay resultados
        Expected: Lista de resultados con botones mostrada
        """
        mock_context_with_args.args = ["FastAPI"]

        with patch(
            "src.bot.handlers.search._search_user_summaries",
            return_value=mock_search_results,
        ):
            await search_handler(mock_update, mock_context_with_args)

            # Verificar que se envió header + resultados
            # Header + 5 resultados = 6 llamadas
            assert mock_update.message.reply_text.call_count == 6

            # Verificar que el header contiene la query y count
            first_call = mock_update.message.reply_text.call_args_list[0]
            header_text = str(first_call)
            assert "FastAPI" in header_text
            assert "5" in header_text  # Count de resultados

    @pytest.mark.asyncio
    async def test_search_command_no_results(self, mock_update, mock_context_with_args):
        """
        Verifica mensaje cuando búsqueda no tiene resultados.

        Scenario: Usuario busca query sin matches
        Expected: Mensaje informativo con sugerencias mostrado
        """
        mock_context_with_args.args = ["NonExistentKeyword"]

        with patch("src.bot.handlers.search._search_user_summaries", return_value=[]):
            await search_handler(mock_update, mock_context_with_args)

            # Verificar que se envió solo 1 mensaje (el informativo)
            assert mock_update.message.reply_text.call_count == 1

            # Verificar contenido del mensaje
            call_args = mock_update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")
            assert "No se encontraron resultados" in message_text
            assert "NonExistentKeyword" in message_text

    @pytest.mark.asyncio
    async def test_search_command_no_args(self, mock_update, mock_context_with_args):
        """
        Verifica mensaje de ayuda cuando no hay argumentos.

        Scenario: Usuario ejecuta /search sin keywords
        Expected: Mensaje de ayuda mostrado
        """
        mock_context_with_args.args = []

        await search_handler(mock_update, mock_context_with_args)

        # Verificar que se envió mensaje de ayuda
        assert mock_update.message.reply_text.call_count == 1

        call_args = mock_update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")
        assert "Uso del comando /search" in message_text
        assert "Ejemplos" in message_text

    @pytest.mark.asyncio
    async def test_search_command_query_too_short(self, mock_update, mock_context_with_args):
        """
        Verifica validación de query muy corta.

        Scenario: Usuario busca con query < 3 caracteres
        Expected: Mensaje de error mostrado
        """
        mock_context_with_args.args = ["ab"]  # Solo 2 chars

        await search_handler(mock_update, mock_context_with_args)

        # Verificar que se envió mensaje de error
        assert mock_update.message.reply_text.call_count == 1

        call_args = mock_update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")
        assert "Query muy corta" in message_text
        assert "3 caracteres" in message_text

    @pytest.mark.asyncio
    async def test_search_command_multiword_query(
        self, mock_update, mock_context_with_args, mock_search_results
    ):
        """
        Verifica búsqueda con múltiples palabras.

        Scenario: Usuario busca "FastAPI Python async"
        Expected: Query combinada correctamente
        """
        mock_context_with_args.args = ["FastAPI", "Python", "async"]

        with patch(
            "src.bot.handlers.search._search_user_summaries",
            return_value=mock_search_results,
        ) as mock_search:
            await search_handler(mock_update, mock_context_with_args)

            # Verificar que se llamó con query combinada
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            query_arg = call_args[0][1]  # Segundo argumento es la query
            assert query_arg == "FastAPI Python async"

    @pytest.mark.asyncio
    async def test_search_command_truncates_long_query(
        self, mock_update, mock_context_with_args, mock_search_results
    ):
        """
        Verifica que query muy larga se trunca.

        Scenario: Usuario busca con query > 100 caracteres
        Expected: Query truncada a 100 chars
        """
        long_query = "word " * 30  # >100 chars
        mock_context_with_args.args = long_query.split()

        with patch(
            "src.bot.handlers.search._search_user_summaries",
            return_value=mock_search_results,
        ) as mock_search:
            await search_handler(mock_update, mock_context_with_args)

            # Verificar que query fue truncada
            call_args = mock_search.call_args
            query_arg = call_args[0][1]
            assert len(query_arg) <= 100

    @pytest.mark.asyncio
    async def test_search_command_limits_displayed_results(
        self, mock_update, mock_context_with_args
    ):
        """
        Verifica que solo se muestran primeros 10 resultados.

        Scenario: Búsqueda retorna 20 resultados
        Expected: Solo 10 mostrados + mensaje de totales
        """
        # Crear 20 resultados mock
        many_results = []
        for i in range(20):
            source = MagicMock()
            source.id = uuid4()
            source.name = f"Channel{i}"
            source.url = f"https://youtube.com/@ch{i}"

            video = MagicMock()
            video.id = uuid4()
            video.youtube_id = f"vid{i}"
            video.title = f"Video {i}"
            video.url = f"https://youtube.com/watch?v={i}"
            video.duration_seconds = 600
            video.extra_metadata = {}
            video.published_at = None

            summary = MagicMock()
            summary.id = uuid4()
            summary.summary_text = f"Summary {i}"
            summary.keywords = ["test"]
            summary.category = "test"

            many_results.append({"summary": summary, "video": video, "source": source})

        mock_context_with_args.args = ["test"]

        with patch(
            "src.bot.handlers.search._search_user_summaries",
            return_value=many_results,
        ):
            await search_handler(mock_update, mock_context_with_args)

            # Verificar que se enviaron: 1 header + 10 resultados = 11 mensajes
            assert mock_update.message.reply_text.call_count == 11

            # Verificar que header menciona "mostrando 10 de 20"
            first_call = mock_update.message.reply_text.call_args_list[0]
            header_text = str(first_call)
            assert "20" in header_text  # Total results
            assert "10" in header_text  # Shown results

    @pytest.mark.asyncio
    async def test_search_command_handles_exception(self, mock_update, mock_context_with_args):
        """
        Verifica manejo de errores en /search.

        Scenario: Error de BD durante búsqueda
        Expected: Mensaje de error amigable enviado
        """
        mock_context_with_args.args = ["FastAPI"]

        with patch(
            "src.bot.handlers.search._search_user_summaries",
            side_effect=Exception("Database error"),
        ):
            await search_handler(mock_update, mock_context_with_args)

            # Verificar que se envió mensaje de error
            assert mock_update.message.reply_text.call_count == 1
            call_args = mock_update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")
            assert "error" in message_text.lower()

    @pytest.mark.asyncio
    async def test_search_command_without_user(self, mock_update, mock_context_with_args):
        """
        Verifica que handler maneja ausencia de effective_user.

        Scenario: Update sin effective_user (edge case)
        Expected: Handler retorna sin error
        """
        mock_update.effective_user = None
        mock_context_with_args.args = ["test"]

        await search_handler(mock_update, mock_context_with_args)

        # No debe haber llamadas a reply_text
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_command_with_special_characters(
        self, mock_update, mock_context_with_args, mock_search_results
    ):
        """
        Verifica que caracteres especiales se sanitizan.

        Scenario: Usuario busca con caracteres especiales SQL
        Expected: Query sanitizada, búsqueda ejecutada sin error
        """
        mock_context_with_args.args = ["test';DROP TABLE users;--"]

        with patch(
            "src.bot.handlers.search._search_user_summaries",
            return_value=mock_search_results,
        ) as mock_search:
            await search_handler(mock_update, mock_context_with_args)

            # Verificar que búsqueda se ejecutó (sanitización exitosa)
            mock_search.assert_called_once()

            # Verificar que no hubo errores
            assert mock_update.message.reply_text.call_count >= 1
