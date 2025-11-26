"""
Tests para la validación de duración de videos en VideoProcessingService.

Verifica que videos que exceden MAX_VIDEO_DURATION_SECONDS se marcan
como SKIPPED en lugar de procesarse.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.config import settings
from src.models.video import VideoStatus
from src.services.video_processing_service import VideoProcessingService


class TestDurationValidation:
    """Tests para validación de duración máxima de videos."""

    @pytest.fixture
    def mock_video_long(self):
        """Fixture de video largo (>35:59)."""
        video = MagicMock()
        video.id = "test-uuid-long"
        video.youtube_id = "long_video_id"
        video.title = "Video de 40 minutos"
        video.url = "https://youtube.com/watch?v=long"
        video.duration_seconds = 2400  # 40 minutos
        video.status = VideoStatus.PENDING
        video.extra_metadata = {}
        return video

    @pytest.fixture
    def mock_video_valid(self):
        """Fixture de video válido (<=35:59)."""
        video = MagicMock()
        video.id = "test-uuid-valid"
        video.youtube_id = "valid_video_id"
        video.title = "Video de 30 minutos"
        video.url = "https://youtube.com/watch?v=valid"
        video.duration_seconds = 1800  # 30 minutos
        video.status = VideoStatus.PENDING
        video.extra_metadata = {}
        return video

    @pytest.mark.asyncio
    async def test_long_video_is_skipped(self, mock_video_long):
        """Verifica que videos >35:59 se marcan como SKIPPED."""
        # Arrange
        service = VideoProcessingService()
        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_video_long

        with patch(
            "src.services.video_processing_service.VideoRepository",
            return_value=mock_repo,
        ):
            # Act
            result = await service.process_video(mock_session, mock_video_long.id)

            # Assert
            assert result.status == VideoStatus.SKIPPED
            assert result.extra_metadata["skip_reason"] == "duration_exceeded"
            assert result.extra_metadata["actual_duration_seconds"] == 2400
            assert (
                result.extra_metadata["max_allowed_seconds"] == settings.MAX_VIDEO_DURATION_SECONDS
            )

    @pytest.mark.asyncio
    async def test_valid_video_is_processed(self, mock_video_valid):
        """Verifica que videos <=35:59 NO se marcan como SKIPPED."""
        # Arrange
        service = VideoProcessingService()
        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = mock_video_valid

        # Mock de servicios downstream para evitar ejecución real
        service._download_audio = AsyncMock(return_value="path/to/audio.mp3")
        service._transcribe_audio = AsyncMock(return_value=MagicMock())
        service._create_summary = AsyncMock(return_value=MagicMock())
        service._cleanup_audio_file = MagicMock()

        with patch(
            "src.services.video_processing_service.VideoRepository",
            return_value=mock_repo,
        ):
            # Act
            result = await service.process_video(mock_session, mock_video_valid.id)

            # Assert
            assert result.status != VideoStatus.SKIPPED
            # No debe tener skip_reason en metadata
            assert "skip_reason" not in (result.extra_metadata or {})

    def test_format_duration_helper(self):
        """Verifica que _format_duration() formatea correctamente."""
        service = VideoProcessingService()

        # Test MM:SS format
        assert service._format_duration(125) == "2:05"
        assert service._format_duration(2159) == "35:59"
        assert service._format_duration(60) == "1:00"

        # Test HH:MM:SS format
        assert service._format_duration(3665) == "1:01:05"
        assert service._format_duration(7200) == "2:00:00"
        assert service._format_duration(3600) == "1:00:00"


class TestVideoRepository:
    """Tests para métodos de VideoRepository relacionados con SKIPPED."""

    def test_get_skipped_videos(self):
        """Verifica que get_skipped_videos() filtra correctamente."""
        # Este test requiere BD real, se implementará en tests de integración
        pass

    def test_get_stats_by_status(self):
        """Verifica que get_stats_by_status() cuenta SKIPPEDs."""
        # Este test requiere BD real, se implementará en tests de integración
        pass
