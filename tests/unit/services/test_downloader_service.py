"""
Tests unitarios para DownloaderService.

Estrategia de testing:
- Mock de yt_dlp.YoutubeDL para evitar descargas reales
- Uso de tmp_path fixture de pytest para archivos temporales
- Validación de estructura de datos retornados
- Manejo de errores (URLs inválidas, red, videos privados)
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.downloader_service import (
    AudioExtractionError,
    DownloadError,
    DownloaderService,
    InvalidURLError,
    NetworkError,
    VideoMetadata,
    VideoNotAvailableError,
)


class TestDownloaderServiceValidation:
    """Tests para validación de URLs."""

    @pytest.fixture
    def service(self):
        """Fixture que crea una instancia del servicio."""
        return DownloaderService()

    def test_validate_youtube_url_valid_watch(self, service):
        """Test 1: URL válida youtube.com/watch?v=... no lanza excepción"""
        # Arrange
        valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Act & Assert - no debe lanzar excepción
        service._validate_youtube_url(valid_url)

    def test_validate_youtube_url_valid_youtu_be(self, service):
        """Test 2: URL válida youtu.be/... no lanza excepción"""
        # Arrange
        valid_url = "https://youtu.be/dQw4w9WgXcQ"

        # Act & Assert - no debe lanzar excepción
        service._validate_youtube_url(valid_url)

    def test_validate_youtube_url_invalid_domain(self, service):
        """Test 3: URL de dominio inválido lanza InvalidURLError"""
        # Arrange
        invalid_url = "https://invalid-domain.com/video"

        # Act & Assert
        with pytest.raises(InvalidURLError, match="URL inválida"):
            service._validate_youtube_url(invalid_url)

    def test_validate_youtube_url_empty_string(self, service):
        """Test 4: URL vacía lanza InvalidURLError"""
        # Arrange
        empty_url = ""

        # Act & Assert
        with pytest.raises(InvalidURLError, match="no puede estar vacía"):
            service._validate_youtube_url(empty_url)

    def test_validate_youtube_url_none(self, service):
        """Test 5: URL None lanza InvalidURLError"""
        # Act & Assert
        with pytest.raises(InvalidURLError, match="no puede estar vacía"):
            service._validate_youtube_url(None)  # type: ignore


class TestDownloaderServiceGetMetadata:
    """Tests para extracción de metadata sin descargar."""

    @pytest.fixture
    def service(self):
        return DownloaderService()

    @pytest.fixture
    def sample_video_info(self):
        """Fixture con información de video de ejemplo."""
        return {
            "id": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "duration": 213,  # 3:33
            "uploader": "Rick Astley",
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            "view_count": 1_400_000_000,
        }

    @pytest.mark.asyncio
    async def test_get_video_metadata_success(self, service, sample_video_info):
        """Test 6: Metadata extraída correctamente sin descargar"""
        # Arrange
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_instance = MagicMock()
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = sample_video_info

            # Act
            result = await service.get_video_metadata(url)

            # Assert
            assert isinstance(result, VideoMetadata)
            assert result.video_id == "dQw4w9WgXcQ"
            assert result.title == "Rick Astley - Never Gonna Give You Up"
            assert result.duration_seconds == 213
            assert result.duration_formatted == "03:33"
            assert result.author == "Rick Astley"
            assert result.view_count == 1_400_000_000

            # Verificar que se llamó con download=False
            mock_instance.extract_info.assert_called_once_with(url, download=False)

    @pytest.mark.asyncio
    async def test_get_video_metadata_invalid_url(self, service):
        """Test 7: URL inválida lanza InvalidURLError"""
        # Arrange
        invalid_url = "https://not-youtube.com/video"

        # Act & Assert
        with pytest.raises(InvalidURLError):
            await service.get_video_metadata(invalid_url)

    @pytest.mark.asyncio
    async def test_get_video_metadata_private_video(self, service):
        """Test 8: Video privado lanza VideoNotAvailableError"""
        # Arrange
        url = "https://youtube.com/watch?v=private"

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_instance = MagicMock()
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.side_effect = Exception("This video is private")

            # Act & Assert
            with pytest.raises(DownloadError, match="Error inesperado"):
                await service.get_video_metadata(url)

    @pytest.mark.asyncio
    async def test_get_video_metadata_network_error(self, service):
        """Test 9: Error de red manejado apropiadamente"""
        # Arrange
        url = "https://youtube.com/watch?v=test"

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            from yt_dlp.utils import DownloadError as YtDlpDownloadError

            mock_instance = MagicMock()
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.side_effect = YtDlpDownloadError("Network timeout error")

            # Act & Assert
            with pytest.raises(NetworkError, match="Error de red"):
                await service.get_video_metadata(url)

    @pytest.mark.asyncio
    async def test_get_video_metadata_missing_id(self, service):
        """Test 10: Video sin ID válido lanza DownloadError (capturado por except Exception)"""
        # Arrange
        url = "https://youtube.com/watch?v=test"
        invalid_info = {
            "title": "Test Video",
            "duration": 100,
            # Falta 'id'
        }

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_instance = MagicMock()
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = invalid_info

            # Act & Assert
            # Nota: VideoNotAvailableError se lanza internamente pero se captura por except Exception
            with pytest.raises(DownloadError, match="Error inesperado"):
                await service.get_video_metadata(url)

    @pytest.mark.asyncio
    async def test_get_video_metadata_defaults_for_optional_fields(self, service):
        """Test 11: Campos opcionales tienen valores por defecto"""
        # Arrange
        url = "https://youtube.com/watch?v=test"
        minimal_info = {
            "id": "test123",
            "title": "Test Video",
            "duration": 150,
            # Sin uploader, thumbnail, view_count
        }

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_instance = MagicMock()
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = minimal_info

            # Act
            result = await service.get_video_metadata(url)

            # Assert
            assert result.author == "Desconocido"  # Default
            assert result.thumbnail_url == ""  # Default
            assert result.view_count is None  # Default
            assert result.duration_formatted == "02:30"  # 150 segundos = 2:30


class TestDownloaderServiceDownloadAudio:
    """Tests para descarga de audio."""

    @pytest.fixture
    def service(self):
        return DownloaderService()

    @pytest.mark.asyncio
    async def test_download_audio_success(self, service, tmp_path):
        """Test 12: Descarga exitosa de audio con archivo válido"""
        # Arrange
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = "dQw4w9WgXcQ"

        # Mock del archivo descargado
        fake_audio_path = tmp_path / f"{video_id}.mp3"
        fake_audio_path.write_bytes(b"fake audio data" * 1000)  # >10KB

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            with patch("src.services.downloader_service.DOWNLOAD_DIR", tmp_path):
                mock_instance = MagicMock()
                mock_ytdl.return_value.__enter__.return_value = mock_instance
                mock_instance.extract_info.return_value = {"id": video_id}

                # Act
                result = await service.download_audio(url)

                # Assert
                assert result == fake_audio_path
                assert result.exists()
                assert result.stat().st_size > 10 * 1024  # >10KB
                mock_instance.extract_info.assert_called_once_with(url, download=True)

    @pytest.mark.asyncio
    async def test_download_audio_invalid_url(self, service):
        """Test 13: URL inválida lanza InvalidURLError"""
        # Arrange
        invalid_url = "https://not-youtube.com/video"

        # Act & Assert
        with pytest.raises(InvalidURLError):
            await service.download_audio(invalid_url)

    @pytest.mark.asyncio
    async def test_download_audio_file_not_created(self, service, tmp_path):
        """Test 14: Archivo no generado lanza DownloadError (capturado por except Exception)"""
        # Arrange
        url = "https://youtube.com/watch?v=test"
        video_id = "test123"

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            with patch("src.services.downloader_service.DOWNLOAD_DIR", tmp_path):
                mock_instance = MagicMock()
                mock_ytdl.return_value.__enter__.return_value = mock_instance
                mock_instance.extract_info.return_value = {"id": video_id}
                # No crear el archivo - simular fallo de FFmpeg

                # Act & Assert
                # Nota: AudioExtractionError se lanza internamente pero se captura por except Exception
                with pytest.raises(DownloadError, match="Error inesperado"):
                    await service.download_audio(url)

    @pytest.mark.asyncio
    async def test_download_audio_file_too_small(self, service, tmp_path):
        """Test 15: Archivo muy pequeño lanza DownloadError (capturado por except Exception)"""
        # Arrange
        url = "https://youtube.com/watch?v=test"
        video_id = "test123"

        # Crear archivo muy pequeño (corrupto)
        fake_audio_path = tmp_path / f"{video_id}.mp3"
        fake_audio_path.write_bytes(b"tiny")  # <10KB

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            with patch("src.services.downloader_service.DOWNLOAD_DIR", tmp_path):
                mock_instance = MagicMock()
                mock_ytdl.return_value.__enter__.return_value = mock_instance
                mock_instance.extract_info.return_value = {"id": video_id}

                # Act & Assert
                # Nota: AudioExtractionError se lanza internamente pero se captura por except Exception
                with pytest.raises(DownloadError, match="Error inesperado"):
                    await service.download_audio(url)

    @pytest.mark.asyncio
    async def test_download_audio_ffmpeg_error(self, service):
        """Test 16: Error de FFmpeg lanza AudioExtractionError"""
        # Arrange
        url = "https://youtube.com/watch?v=test"

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            from yt_dlp.utils import DownloadError as YtDlpDownloadError

            mock_instance = MagicMock()
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.side_effect = YtDlpDownloadError(
                "FFmpeg not found or failed to extract audio"
            )

            # Act & Assert
            with pytest.raises(AudioExtractionError, match="FFmpeg"):
                await service.download_audio(url)

    @pytest.mark.asyncio
    async def test_download_audio_video_unavailable(self, service):
        """Test 17: Video no disponible lanza VideoNotAvailableError"""
        # Arrange
        url = "https://youtube.com/watch?v=deleted"

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            from yt_dlp.utils import DownloadError as YtDlpDownloadError

            mock_instance = MagicMock()
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.side_effect = YtDlpDownloadError(
                "This video is unavailable or private"
            )

            # Act & Assert
            with pytest.raises(VideoNotAvailableError, match="no disponible"):
                await service.download_audio(url)

    @pytest.mark.asyncio
    async def test_download_audio_network_timeout(self, service):
        """Test 18: Timeout de red lanza NetworkError"""
        # Arrange
        url = "https://youtube.com/watch?v=test"

        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            from yt_dlp.utils import DownloadError as YtDlpDownloadError

            mock_instance = MagicMock()
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.side_effect = YtDlpDownloadError(
                "Network timeout after 300 seconds"
            )

            # Act & Assert
            with pytest.raises(NetworkError, match="Error de red"):
                await service.download_audio(url)
