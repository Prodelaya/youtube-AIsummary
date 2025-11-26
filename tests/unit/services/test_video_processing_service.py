"""
Tests unitarios para VideoProcessingService.

Estrategia de testing:
- Mock de todos los servicios dependientes (downloader, transcriber, summarizer)
- Mock de repositorios (VideoRepository, TranscriptionRepository)
- Validación de transiciones de estado del video
- Manejo de errores en cada fase del pipeline
"""

from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.models import Video
from src.models.video import VideoStatus
from src.services.video_processing_service import (
    InvalidVideoStateError,
    VideoNotFoundError,
    VideoProcessingService,
)


class TestVideoProcessingServiceInitialization:
    """Tests para inicialización del servicio."""

    @patch("src.services.video_processing_service.get_transcription_service")
    @patch("src.services.video_processing_service.SummarizationService")
    @patch("src.services.video_processing_service.DownloaderService")
    def test_service_initializes_with_dependencies(
        self, mock_downloader, mock_summarizer, mock_transcriber
    ):
        """Test 1: Servicio se inicializa con todas las dependencias"""
        # Arrange
        mock_downloader_instance = Mock()
        mock_transcriber_instance = Mock()
        mock_summarizer_instance = Mock()

        mock_downloader.return_value = mock_downloader_instance
        mock_transcriber.return_value = mock_transcriber_instance
        mock_summarizer.return_value = mock_summarizer_instance

        # Act
        service = VideoProcessingService()

        # Assert
        assert service.downloader == mock_downloader_instance
        assert service.transcriber == mock_transcriber_instance
        assert service.summarizer == mock_summarizer_instance


class TestVideoProcessingServiceValidation:
    """Tests para validación de videos antes de procesar."""

    @pytest.fixture
    def service(self):
        """Fixture con servicio mockeado."""
        with patch("src.services.video_processing_service.get_transcription_service"):
            with patch("src.services.video_processing_service.SummarizationService"):
                with patch("src.services.video_processing_service.DownloaderService"):
                    return VideoProcessingService()

    @pytest.fixture
    def mock_session(self):
        """Fixture con sesión de BD mockeada."""
        return Mock()

    @pytest.mark.asyncio
    async def test_process_video_not_found(self, service, mock_session):
        """Test 2: Video no encontrado lanza VideoNotFoundError"""
        # Arrange
        video_id = uuid4()

        with patch("src.services.video_processing_service.VideoRepository") as mock_repo:
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = None  # Video no existe

            # Act & Assert
            with pytest.raises(VideoNotFoundError, match="no encontrado"):
                await service.process_video(mock_session, video_id)

    @pytest.mark.asyncio
    async def test_process_video_invalid_state_downloading(self, service, mock_session):
        """Test 3: Video en estado 'downloading' lanza InvalidVideoStateError"""
        # Arrange
        video_id = uuid4()
        video = Mock(spec=Video)
        video.status = VideoStatus.DOWNLOADING  # Estado inválido

        with patch("src.services.video_processing_service.VideoRepository") as mock_repo:
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = video

            # Act & Assert
            with pytest.raises(InvalidVideoStateError, match="estado 'downloading'"):
                await service.process_video(mock_session, video_id)

    @pytest.mark.asyncio
    async def test_process_video_invalid_state_completed(self, service, mock_session):
        """Test 4: Video en estado 'completed' lanza InvalidVideoStateError"""
        # Arrange
        video_id = uuid4()
        video = Mock(spec=Video)
        video.status = VideoStatus.COMPLETED  # Ya completado

        with patch("src.services.video_processing_service.VideoRepository") as mock_repo:
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = video

            # Act & Assert
            with pytest.raises(InvalidVideoStateError, match="solo se pueden procesar"):
                await service.process_video(mock_session, video_id)

    @pytest.mark.asyncio
    async def test_process_video_pending_state_accepted(self, service, mock_session):
        """Test 5: Video en estado 'pending' es aceptado para procesar"""
        # Arrange
        video_id = uuid4()
        video = Mock(spec=Video)
        video.status = VideoStatus.PENDING  # Estado válido
        video.url = "https://youtube.com/watch?v=test"
        video.youtube_id = "test123"
        video.title = "Test Video"
        video.duration_seconds = 300

        # Mock de servicios y repositorios
        with patch("src.services.video_processing_service.VideoRepository") as mock_repo:
            with patch.object(service.downloader, "get_video_metadata") as mock_metadata:
                with patch.object(service.downloader, "download_audio") as mock_download:
                    with patch.object(service.transcriber, "transcribe_audio") as mock_transcribe:
                        with patch("src.services.video_processing_service.TranscriptionRepository"):
                            with patch.object(
                                service.summarizer, "generate_summary"
                            ) as mock_summarize:
                                # Setup mocks
                                mock_repo_instance = Mock()
                                mock_repo.return_value = mock_repo_instance
                                mock_repo_instance.get_by_id.return_value = video

                                mock_metadata.return_value = Mock(
                                    video_id="test123", title="Test Video", duration_seconds=300
                                )

                                mock_download.return_value = Path("/tmp/audio.mp3")

                                mock_transcription_result = Mock()
                                mock_transcription_result.text = "Test transcription"
                                mock_transcription_result.language = "es"
                                mock_transcription_result.duration = 300
                                mock_transcribe.return_value = mock_transcription_result

                                mock_summary = Mock()
                                mock_summarize.return_value = mock_summary

                                # Act
                                # No debe lanzar InvalidVideoStateError
                                try:
                                    await service.process_video(mock_session, video_id)
                                except InvalidVideoStateError:
                                    pytest.fail(
                                        "No debería lanzar InvalidVideoStateError para pending"
                                    )
                                except Exception:
                                    # Otros errores son esperados en este test simplificado
                                    pass

    @pytest.mark.asyncio
    async def test_process_video_failed_state_accepted(self, service, mock_session):
        """Test 6: Video en estado 'failed' puede ser reprocesado"""
        # Arrange
        video_id = uuid4()
        video = Mock(spec=Video)
        video.status = VideoStatus.FAILED  # Se permite reprocesar
        video.url = "https://youtube.com/watch?v=test"
        video.youtube_id = "test123"
        video.title = "Test Video"
        video.duration_seconds = 300

        with patch("src.services.video_processing_service.VideoRepository") as mock_repo:
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = video

            # Act
            # No debe lanzar InvalidVideoStateError
            try:
                await service.process_video(mock_session, video_id)
            except InvalidVideoStateError:
                pytest.fail("No debería lanzar InvalidVideoStateError para failed")
            except Exception:
                # Otros errores son esperados
                pass


class TestVideoProcessingServiceDurationValidation:
    """Tests para validación de duración máxima de videos."""

    @pytest.fixture
    def service(self):
        with patch("src.services.video_processing_service.get_transcription_service"):
            with patch("src.services.video_processing_service.SummarizationService"):
                with patch("src.services.video_processing_service.DownloaderService"):
                    return VideoProcessingService()

    @pytest.mark.asyncio
    async def test_process_video_duration_exceeds_max(self, service):
        """Test 7: Video que excede duración máxima se marca como SKIPPED"""
        # Arrange
        video_id = uuid4()
        mock_session = Mock()

        # Video muy largo (2 horas = 7200 segundos, máximo es 3600)
        video = Mock(spec=Video)
        video.status = VideoStatus.PENDING
        video.duration_seconds = 7200  # 2 horas
        video.extra_metadata = {}

        with patch("src.services.video_processing_service.VideoRepository") as mock_repo:
            with patch("src.services.video_processing_service.settings") as mock_settings:
                mock_settings.MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hora máx

                mock_repo_instance = Mock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.get_by_id.return_value = video

                # Act
                result = await service.process_video(mock_session, video_id)

                # Assert
                assert result.status == VideoStatus.SKIPPED
                assert "skip_reason" in result.extra_metadata
                assert result.extra_metadata["skip_reason"] == "duration_exceeded"
                mock_session.commit.assert_called()


class TestVideoProcessingServiceFormatDuration:
    """Tests para el método auxiliar de formateo de duración."""

    @pytest.fixture
    def service(self):
        with patch("src.services.video_processing_service.get_transcription_service"):
            with patch("src.services.video_processing_service.SummarizationService"):
                with patch("src.services.video_processing_service.DownloaderService"):
                    return VideoProcessingService()

    def test_format_duration_seconds_only(self, service):
        """Test 8: Formateo de duración solo segundos"""
        # Act
        result = service._format_duration(45)

        # Assert
        assert result == "0:45"  # Formato sin ceros iniciales

    def test_format_duration_minutes_seconds(self, service):
        """Test 9: Formateo de duración minutos y segundos"""
        # Act
        result = service._format_duration(125)  # 2:05

        # Assert
        assert result == "2:05"  # Formato sin ceros iniciales en horas

    def test_format_duration_hours(self, service):
        """Test 10: Formateo de duración con horas"""
        # Act
        result = service._format_duration(3665)  # 1:01:05

        # Assert
        assert result == "1:01:05"  # Formato sin ceros iniciales en horas

    def test_format_duration_zero(self, service):
        """Test 11: Formateo de duración cero"""
        # Act
        result = service._format_duration(0)

        # Assert
        assert result == "0:00"  # Formato sin ceros iniciales
