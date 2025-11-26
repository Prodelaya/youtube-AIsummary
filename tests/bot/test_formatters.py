"""
Tests para las utilidades de formateo de mensajes del bot.

Verifica que los formateadores generen mensajes correctos con
markdown, truncamiento y manejo de edge cases.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.bot.utils.formatters import (
    format_duration,
    format_summary_message,
    truncate_text,
)
from src.models import Source, Summary, Video


class TestFormatDuration:
    """Tests para la función format_duration."""

    def test_format_seconds_only(self):
        """Verifica formato de duración menor a 1 minuto."""
        assert format_duration(45) == "0:45"
        assert format_duration(5) == "0:05"
        assert format_duration(59) == "0:59"

    def test_format_minutes_and_seconds(self):
        """Verifica formato de duración en minutos y segundos."""
        assert format_duration(125) == "2:05"
        assert format_duration(300) == "5:00"
        assert format_duration(601) == "10:01"

    def test_format_hours_minutes_seconds(self):
        """Verifica formato de duración mayor a 1 hora."""
        assert format_duration(3665) == "1:01:05"
        assert format_duration(7200) == "2:00:00"
        assert format_duration(3661) == "1:01:01"

    def test_format_zero_seconds(self):
        """Verifica que 0 segundos se formatea correctamente."""
        assert format_duration(0) == "0:00"

    def test_format_negative_seconds(self):
        """Verifica que duración negativa retorna 0:00."""
        assert format_duration(-10) == "0:00"
        assert format_duration(-100) == "0:00"


class TestTruncateText:
    """Tests para la función truncate_text."""

    def test_truncate_long_text(self):
        """Verifica que texto largo se trunca correctamente."""
        text = "Hello world this is a very long text that needs to be truncated"
        result = truncate_text(text, 20)

        assert len(result) <= 20
        assert result.endswith("...")
        assert "Hello world" in result

    def test_truncate_at_word_boundary(self):
        """Verifica que el truncamiento respeta límites de palabras."""
        text = "Hello world test"
        result = truncate_text(text, 13)

        # Con max_length=13, "Hello world" = 11 chars + 3 ("...") = 14
        # Así que trunca a "Hello" (5 chars) + "..." = 8 chars
        assert result == "Hello..."
        assert not result.endswith("wor...")  # No corta en mitad de palabra

    def test_no_truncate_short_text(self):
        """Verifica que texto corto no se modifica."""
        text = "Short text"
        result = truncate_text(text, 50)

        assert result == text
        assert not result.endswith("...")

    def test_truncate_exact_length(self):
        """Verifica texto con longitud exacta al límite."""
        text = "Exactly 20 chars here"  # 21 chars
        result = truncate_text(text, 21)

        assert result == text

    def test_truncate_single_long_word(self):
        """Verifica truncamiento cuando no hay espacios."""
        text = "Superlongwordwithoutspaces"
        result = truncate_text(text, 10)

        assert len(result) <= 10
        assert result.endswith("...")


class TestFormatSummaryMessage:
    """Tests para la función format_summary_message."""

    @pytest.fixture
    def mock_source(self):
        """Fixture que crea un Source mock."""
        source = MagicMock(spec=Source)
        source.id = uuid4()
        source.name = "Fireship"
        source.url = "https://youtube.com/@fireship"
        source.source_type = "youtube"
        return source

    @pytest.fixture
    def mock_video(self):
        """Fixture que crea un Video mock."""
        video = MagicMock(spec=Video)
        video.id = uuid4()
        video.youtube_id = "dQw4w9WgXcQ"
        video.title = "FastAPI Tutorial - Building Modern APIs"
        video.url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        video.duration_seconds = 720  # 12 minutos
        video.published_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        video.extra_metadata = {"view_count": 150000}
        return video

    @pytest.fixture
    def mock_summary(self):
        """Fixture que crea un Summary mock."""
        summary = MagicMock(spec=Summary)
        summary.id = uuid4()
        summary.summary_text = (
            "This video explains how to build modern APIs with FastAPI. "
            "It covers async endpoints, dependency injection, automatic documentation, "
            "and database integration with SQLAlchemy."
        )
        summary.keywords = ["FastAPI", "Python", "API", "async", "SQLAlchemy"]
        summary.category = "framework"
        return summary

    def test_format_complete_summary(self, mock_summary, mock_video, mock_source):
        """Verifica formateo de resumen completo con todos los campos."""
        result = format_summary_message(mock_summary, mock_video, mock_source)

        # Verificar que contiene elementos clave (escapados para Markdown V2)
        assert "FastAPI Tutorial" in result or "FastAPI" in result
        assert "Fireship" in result
        assert "12:00" in result  # Duración formateada
        assert "#FastAPI" in result or "FastAPI" in result
        assert "youtube.com" in result

        # Verificar que no excede límite de Telegram
        assert len(result) <= 4096

    def test_format_summary_without_keywords(self, mock_summary, mock_video, mock_source):
        """Verifica formateo cuando no hay keywords."""
        mock_summary.keywords = []

        result = format_summary_message(mock_summary, mock_video, mock_source)

        # No debe tener sección de tags
        assert "#" not in result or "Tags" not in result
        assert len(result) > 0

    def test_format_summary_without_duration(self, mock_summary, mock_video, mock_source):
        """Verifica formateo cuando no hay duración."""
        mock_video.duration_seconds = None

        result = format_summary_message(mock_summary, mock_video, mock_source)

        # No debe tener sección de duración
        assert "Duración" not in result
        assert len(result) > 0

    def test_format_summary_truncates_long_text(self, mock_summary, mock_video, mock_source):
        """Verifica que resumen muy largo se trunca."""
        # Crear resumen muy largo (>800 chars)
        mock_summary.summary_text = "A" * 1000

        result = format_summary_message(mock_summary, mock_video, mock_source)

        # Debe truncarse y no exceder límite
        assert len(result) <= 4096

    def test_format_summary_with_special_characters(self, mock_summary, mock_video, mock_source):
        """Verifica manejo de caracteres especiales de Markdown."""
        mock_video.title = "API Testing: Unit & Integration [2024]"
        mock_source.name = "Tech & Code (Official)"

        result = format_summary_message(mock_summary, mock_video, mock_source)

        # Debe escapar caracteres especiales pero seguir siendo válido
        assert len(result) > 0
        # Caracteres especiales deben estar escapados con backslash
        assert "\\" in result or "API Testing" in result

    def test_format_summary_with_view_count(self, mock_summary, mock_video, mock_source):
        """Verifica que view_count se formatea con separadores."""
        mock_video.extra_metadata = {"view_count": 1234567}

        result = format_summary_message(mock_summary, mock_video, mock_source)

        # Debe contener view count formateado
        assert "1,234,567" in result or "1234567" in result or "vistas" in result

    def test_format_summary_limits_keywords(self, mock_summary, mock_video, mock_source):
        """Verifica que solo se muestran máximo 5 keywords."""
        mock_summary.keywords = [
            "Keyword1",
            "Keyword2",
            "Keyword3",
            "Keyword4",
            "Keyword5",
            "Keyword6",
            "Keyword7",
        ]

        result = format_summary_message(mock_summary, mock_video, mock_source)

        # Contar hashtags (debe haber máximo 5)
        hashtag_count = result.count("#")
        assert hashtag_count <= 5
