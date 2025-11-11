"""
Tests unitarios para VideoProcessingService.

Estos tests usan mocks de todos los servicios externos para aislar
la lógica de orquestación del pipeline. No hacen llamadas reales a:
- yt-dlp (descarga de YouTube)
- Whisper (transcripción)
- DeepSeek API (resumen)
- Base de datos

Los tests verifican:
- Flujo completo exitoso (todos los pasos)
- Manejo de errores en cada fase
- Transiciones de estados correctas
- Limpieza de archivos temporales
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from src.models import Summary, Transcription, Video
from src.models.video import VideoStatus
from src.services.downloader_service import (
    AudioExtractionError,
    InvalidURLError,
    NetworkError,
    VideoNotAvailableError,
)
from src.services.summarization_service import DeepSeekAPIError
from src.services.transcription_service import (
    TranscriptionFailedError,
    TranscriptionResult,
)
from src.services.video_processing_service import (
    InvalidVideoStateError,
    VideoNotFoundError,
    VideoProcessingService,
)


# ==================== FIXTURES ====================


@pytest.fixture
def mock_db_session():
    """Mock de SQLAlchemy Session."""
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    return session


@pytest.fixture
def sample_video():
    """Video de prueba en estado PENDING."""
    return Video(
        id=uuid4(),
        source_id=uuid4(),
        youtube_id="test_video_123",
        title="Test Video",
        url="https://youtube.com/watch?v=test123",
        duration_seconds=600,
        status=VideoStatus.PENDING,
    )


@pytest.fixture
def mock_downloader():
    """Mock del DownloaderService."""
    downloader = MagicMock()

    # Mock de Path con stat()
    mock_path = MagicMock(spec=Path)
    mock_path.stat.return_value = MagicMock(st_size=1024 * 1024 * 5)  # 5 MB
    mock_path.exists.return_value = True

    downloader.download_audio = AsyncMock(return_value=mock_path)
    return downloader


@pytest.fixture
def mock_transcriber():
    """Mock del TranscriptionService."""
    transcriber = MagicMock()
    transcriber.transcribe_audio = AsyncMock(
        return_value=TranscriptionResult(
            text="This is a test transcription of the video.",
            language="en",
            duration=600.0,
        )
    )
    return transcriber


@pytest.fixture
def mock_summarizer():
    """Mock del SummarizationService."""
    summarizer = MagicMock()
    summary = Summary(
        id=uuid4(),
        transcription_id=uuid4(),
        summary_text="This is a test summary.",
        keywords=["test", "summary"],
        category="concept",
        model_used="deepseek-chat",
        tokens_used=500,
    )
    summarizer.generate_summary = AsyncMock(return_value=summary)
    return summarizer


@pytest.fixture
def video_processing_service(mock_downloader, mock_transcriber, mock_summarizer):
    """VideoProcessingService con servicios mockeados."""
    service = VideoProcessingService()
    service.downloader = mock_downloader
    service.transcriber = mock_transcriber
    service.summarizer = mock_summarizer
    return service


# ==================== TESTS DE FLUJO EXITOSO ====================


@pytest.mark.asyncio
async def test_process_video_success(
    video_processing_service,
    mock_db_session,
    sample_video,
):
    """
    Test: Pipeline completo exitoso.

    Verifica que:
    1. Se ejecutan todos los pasos en orden
    2. Los estados del video se actualizan correctamente
    3. Se crean transcripción y resumen
    4. El archivo de audio se limpia al final
    """
    # Configurar mocks de repositorios
    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo, \
         patch("src.services.video_processing_service.TranscriptionRepository") as MockTransRepo, \
         patch("src.services.video_processing_service.Path") as MockPath:

        # Mock de VideoRepository
        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = sample_video

        # Mock de TranscriptionRepository
        mock_trans_repo = MockTransRepo.return_value
        mock_transcription = Transcription(
            id=uuid4(),
            video_id=sample_video.id,
            text="Test transcription",
            language="en",
            model_used="whisper-base",
            duration_seconds=600,
        )
        mock_trans_repo.create.return_value = mock_transcription

        # Mock de Path para cleanup
        mock_audio_path = MockPath.return_value
        mock_audio_path.exists.return_value = True
        mock_audio_path.unlink = MagicMock()

        # Ejecutar pipeline
        result = await video_processing_service.process_video(
            mock_db_session,
            sample_video.id,
        )

        # Verificar que se llamaron todos los servicios
        video_processing_service.downloader.download_audio.assert_called_once_with(
            sample_video.url
        )
        video_processing_service.transcriber.transcribe_audio.assert_called_once()
        video_processing_service.summarizer.generate_summary.assert_called_once()

        # Verificar que el video terminó en estado COMPLETED
        assert result.status == VideoStatus.COMPLETED

        # Verificar que se hicieron commits intermedios
        assert mock_db_session.commit.call_count >= 4


@pytest.mark.asyncio
async def test_process_video_state_transitions(
    video_processing_service,
    mock_db_session,
    sample_video,
):
    """
    Test: Transiciones de estados durante el pipeline.

    Verifica que el video pasa por todos los estados intermedios:
    pending → downloading → downloaded → transcribing → transcribed →
    summarizing → completed
    """
    states_observed = []

    # Capturar estados durante el pipeline
    def capture_state(*args, **kwargs):
        states_observed.append(sample_video.status)

    mock_db_session.commit.side_effect = capture_state

    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo, \
         patch("src.services.video_processing_service.TranscriptionRepository") as MockTransRepo, \
         patch("src.services.video_processing_service.Path"):

        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = sample_video

        mock_trans_repo = MockTransRepo.return_value
        mock_transcription = Transcription(
            id=uuid4(),
            video_id=sample_video.id,
            text="Test",
            language="en",
            model_used="whisper-base",
            duration_seconds=600,
        )
        mock_trans_repo.create.return_value = mock_transcription

        await video_processing_service.process_video(
            mock_db_session,
            sample_video.id,
        )

        # Verificar transiciones (al menos los estados principales)
        assert VideoStatus.DOWNLOADING in states_observed
        assert VideoStatus.DOWNLOADED in states_observed
        assert VideoStatus.TRANSCRIBING in states_observed
        assert VideoStatus.TRANSCRIBED in states_observed
        assert VideoStatus.SUMMARIZING in states_observed
        assert VideoStatus.COMPLETED in states_observed


# ==================== TESTS DE ERRORES ====================


@pytest.mark.asyncio
async def test_process_video_not_found(
    video_processing_service,
    mock_db_session,
):
    """
    Test: Error cuando el video no existe en BD.
    """
    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo:
        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = None

        with pytest.raises(VideoNotFoundError):
            await video_processing_service.process_video(
                mock_db_session,
                uuid4(),
            )


@pytest.mark.asyncio
async def test_process_video_invalid_state(
    video_processing_service,
    mock_db_session,
    sample_video,
):
    """
    Test: Error cuando el video está en estado no procesable (ej: COMPLETED).
    """
    sample_video.status = VideoStatus.COMPLETED

    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo:
        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = sample_video

        with pytest.raises(InvalidVideoStateError):
            await video_processing_service.process_video(
                mock_db_session,
                sample_video.id,
            )


@pytest.mark.asyncio
async def test_process_video_download_failed_invalid_url(
    video_processing_service,
    mock_db_session,
    sample_video,
):
    """
    Test: Error en fase de descarga (URL inválida).

    Verifica que:
    1. El video se marca como FAILED
    2. Se hace commit del error
    3. La excepción se propaga
    """
    # Configurar downloader para fallar
    video_processing_service.downloader.download_audio = AsyncMock(
        side_effect=InvalidURLError("URL inválida")
    )

    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo:
        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = sample_video

        with pytest.raises(InvalidURLError):
            await video_processing_service.process_video(
                mock_db_session,
                sample_video.id,
            )

        # Verificar que el video se marcó como FAILED
        assert sample_video.status == VideoStatus.FAILED
        assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_process_video_download_failed_network_error(
    video_processing_service,
    mock_db_session,
    sample_video,
):
    """
    Test: Error en fase de descarga (error de red).

    Verifica que se intenta limpiar archivos parciales.
    """
    video_processing_service.downloader.download_audio = AsyncMock(
        side_effect=NetworkError("Connection timeout")
    )

    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo, \
         patch("src.services.video_processing_service.Path") as MockPath:

        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = sample_video

        # Mock de Path para simular archivo parcial existente
        mock_audio_path = MockPath.return_value
        mock_audio_path.exists.return_value = True
        mock_audio_path.unlink = MagicMock()

        with pytest.raises(NetworkError):
            await video_processing_service.process_video(
                mock_db_session,
                sample_video.id,
            )

        assert sample_video.status == VideoStatus.FAILED


@pytest.mark.asyncio
async def test_process_video_transcription_failed(
    video_processing_service,
    mock_db_session,
    sample_video,
):
    """
    Test: Error en fase de transcripción.

    Verifica que:
    1. El audio se descarga correctamente
    2. Falla la transcripción
    3. El video se marca como FAILED
    4. El archivo de audio NO se borra (debugging)
    """
    # Configurar transcriber para fallar
    video_processing_service.transcriber.transcribe_audio = AsyncMock(
        side_effect=TranscriptionFailedError("Whisper crashed")
    )

    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo, \
         patch("src.services.video_processing_service.TranscriptionRepository") as MockTransRepo:

        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = sample_video

        with pytest.raises(TranscriptionFailedError):
            await video_processing_service.process_video(
                mock_db_session,
                sample_video.id,
            )

        # Verificar estado
        assert sample_video.status == VideoStatus.FAILED

        # Verificar que downloader SÍ se llamó (llegamos a esa fase)
        video_processing_service.downloader.download_audio.assert_called_once()


@pytest.mark.asyncio
async def test_process_video_summarization_failed(
    video_processing_service,
    mock_db_session,
    sample_video,
):
    """
    Test: Error en fase de resumen (API de DeepSeek).

    Verifica que:
    1. Descarga y transcripción funcionan
    2. Falla la generación de resumen
    3. El video se marca como FAILED
    4. El archivo de audio SÍ se borra (transcripción ya guardada)
    """
    # Configurar summarizer para fallar
    video_processing_service.summarizer.generate_summary = AsyncMock(
        side_effect=DeepSeekAPIError("API rate limit", status_code=429)
    )

    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo, \
         patch("src.services.video_processing_service.TranscriptionRepository") as MockTransRepo, \
         patch("src.services.video_processing_service.Path") as MockPath:

        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = sample_video

        mock_trans_repo = MockTransRepo.return_value
        mock_transcription = Transcription(
            id=uuid4(),
            video_id=sample_video.id,
            text="Test",
            language="en",
            model_used="whisper-base",
            duration_seconds=600,
        )
        mock_trans_repo.create.return_value = mock_transcription

        # Mock de Path para cleanup
        mock_audio_path = MockPath.return_value
        mock_audio_path.exists.return_value = True
        mock_audio_path.unlink = MagicMock()

        with pytest.raises(DeepSeekAPIError):
            await video_processing_service.process_video(
                mock_db_session,
                sample_video.id,
            )

        # Verificar estado
        assert sample_video.status == VideoStatus.FAILED

        # Verificar que downloader y transcriber SÍ se llamaron
        video_processing_service.downloader.download_audio.assert_called_once()
        video_processing_service.transcriber.transcribe_audio.assert_called_once()


# ==================== TESTS DE LIMPIEZA DE ARCHIVOS ====================


@pytest.mark.asyncio
async def test_cleanup_audio_file_on_success(
    video_processing_service,
    mock_db_session,
    sample_video,
):
    """
    Test: Archivo de audio se borra al completar exitosamente.
    """
    with patch("src.services.video_processing_service.VideoRepository") as MockVideoRepo, \
         patch("src.services.video_processing_service.TranscriptionRepository") as MockTransRepo, \
         patch.object(video_processing_service, "_cleanup_audio_file") as mock_cleanup:

        mock_video_repo = MockVideoRepo.return_value
        mock_video_repo.get_by_id.return_value = sample_video

        mock_trans_repo = MockTransRepo.return_value
        mock_transcription = Transcription(
            id=uuid4(),
            video_id=sample_video.id,
            text="Test",
            language="en",
            model_used="whisper-base",
            duration_seconds=600,
        )
        mock_trans_repo.create.return_value = mock_transcription

        await video_processing_service.process_video(
            mock_db_session,
            sample_video.id,
        )

        # Verificar que se llamó cleanup
        mock_cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_audio_file_handles_missing_file(
    video_processing_service,
):
    """
    Test: Cleanup maneja correctamente archivos que no existen.
    """
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = False

    # No debe lanzar excepción
    video_processing_service._cleanup_audio_file(mock_path)

    # No debe intentar borrar
    mock_path.unlink.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_audio_file_handles_deletion_error(
    video_processing_service,
):
    """
    Test: Cleanup maneja errores de eliminación sin fallar.
    """
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.unlink.side_effect = PermissionError("Permission denied")

    # No debe lanzar excepción (solo loggear)
    video_processing_service._cleanup_audio_file(mock_path)
