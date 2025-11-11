"""
Tests de integración para VideoProcessingService.

Estos tests usan:
- Base de datos REAL (con rollback automático)
- Mocks de servicios externos (yt-dlp, Whisper, DeepSeek)
- Validación de persistencia en BD
- Verificación de relaciones entre modelos

NO se hacen llamadas reales a:
- YouTube (descarga)
- Whisper (transcripción)
- DeepSeek API (resumen)

Pero SÍ se valida:
- Creación correcta de registros en BD
- Relaciones Video → Transcription → Summary
- Transacciones y commits intermedios
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models import Summary, Transcription, Video
from src.models.video import VideoStatus
from src.repositories.summary_repository import SummaryRepository
from src.repositories.transcription_repository import TranscriptionRepository
from src.repositories.video_repository import VideoRepository
from src.services.downloader_service import InvalidURLError, NetworkError
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


# ==================== TESTS ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_process_video_full_pipeline_with_db(
    db_session,
    sample_source,
):
    """
    Test de integración: Pipeline completo con BD real.

    Verifica:
    1. Video se crea en BD con estado PENDING
    2. Se ejecuta pipeline completo (mockeado)
    3. Se crean Transcription y Summary en BD
    4. Video termina en estado COMPLETED
    5. Relaciones entre modelos son correctas
    """
    # Crear video de prueba en BD
    video_repo = VideoRepository(db_session)
    video = Video(
        source_id=sample_source.id,
        youtube_id="integration_test_123",
        title="Integration Test Video",
        url="https://youtube.com/watch?v=test123",
        duration_seconds=600,
        status=VideoStatus.PENDING,
    )
    created_video = video_repo.create(video)
    db_session.commit()

    # Configurar mocks de servicios externos
    mock_downloader = MagicMock()

    # Mock de Path con stat()
    mock_audio_path = MagicMock(spec=Path)
    mock_audio_path.stat.return_value = MagicMock(st_size=1024 * 1024 * 5)  # 5 MB
    mock_audio_path.exists.return_value = True

    mock_downloader.download_audio = AsyncMock(return_value=mock_audio_path)

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe_audio = AsyncMock(
        return_value=TranscriptionResult(
            text="This is an integration test transcription of the video content.",
            language="en",
            duration=600.0,
        )
    )

    mock_summarizer = MagicMock()

    # Crear servicio con mocks
    service = VideoProcessingService()
    service.downloader = mock_downloader
    service.transcriber = mock_transcriber
    service.summarizer = mock_summarizer

    # Mock de generate_summary para que persista en BD real
    async def mock_generate_summary(session, transcription_id):
        # Obtener transcription
        trans_repo = TranscriptionRepository(session)
        transcription = trans_repo.get_by_id(transcription_id)

        # Crear summary
        summary = Summary(
            transcription_id=transcription_id,
            summary_text="This is a test summary of the integration test video.",
            keywords=["integration", "test", "video"],
            category="concept",
            model_used="deepseek-chat",
            tokens_used=500,
            input_tokens=400,
            output_tokens=100,
        )

        summary_repo = SummaryRepository(session)
        created_summary = summary_repo.create(summary)
        session.commit()

        return created_summary

    mock_summarizer.generate_summary = mock_generate_summary

    # Mock de cleanup para evitar errores de Path
    with patch.object(service, "_cleanup_audio_file"):
        # Ejecutar pipeline
        result_video = await service.process_video(db_session, created_video.id)

        # Verificar estado final del video
        assert result_video.status == VideoStatus.COMPLETED
        assert result_video.id == created_video.id

        # Verificar que Transcription fue creada en BD
        trans_repo = TranscriptionRepository(db_session)
        transcription = trans_repo.get_by_video_id(created_video.id)
        assert transcription is not None
        assert transcription.video_id == created_video.id
        assert transcription.text == "This is an integration test transcription of the video content."
        assert transcription.language == "en"
        assert transcription.model_used == "whisper-base"

        # Verificar que Summary fue creado en BD
        summary_repo = SummaryRepository(db_session)
        summary = summary_repo.get_by_transcription_id(transcription.id)
        assert summary is not None
        assert summary.transcription_id == transcription.id
        assert "integration test" in summary.summary_text.lower()
        assert summary.keywords == ["integration", "test", "video"]
        assert summary.category == "concept"

        # Verificar relaciones
        # Video → Transcription
        video_with_relations = video_repo.get_by_id(created_video.id)
        assert video_with_relations.transcription is not None
        assert video_with_relations.transcription.id == transcription.id

        # Transcription → Summary
        assert transcription.summary is not None
        assert transcription.summary.id == summary.id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_process_video_download_failure_persists_state(
    db_session,
    sample_source,
):
    """
    Test: Fallo en descarga persiste estado FAILED en BD.
    """
    # Crear video de prueba
    video_repo = VideoRepository(db_session)
    video = Video(
        source_id=sample_source.id,
        youtube_id="fail_download_test",
        title="Fail Download Test",
        url="https://youtube.com/watch?v=invalid",
        duration_seconds=300,
        status=VideoStatus.PENDING,
    )
    created_video = video_repo.create(video)
    db_session.commit()

    # Configurar servicio con downloader que falla
    service = VideoProcessingService()
    service.downloader.download_audio = AsyncMock(
        side_effect=InvalidURLError("URL inválida")
    )

    # Ejecutar pipeline (debe fallar)
    with pytest.raises(InvalidURLError):
        await service.process_video(db_session, created_video.id)

    # Refrescar video desde BD
    db_session.refresh(created_video)

    # Verificar que el estado se persistió
    assert created_video.status == VideoStatus.FAILED

    # Verificar que NO se creó Transcription
    trans_repo = TranscriptionRepository(db_session)
    transcription = trans_repo.get_by_video_id(created_video.id)
    assert transcription is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_process_video_transcription_failure_preserves_download(
    db_session,
    sample_source,
):
    """
    Test: Fallo en transcripción no pierde el progreso de descarga.

    Verifica que aunque falle la transcripción, el video pasa por
    los estados downloading → downloaded antes de fallar.
    """
    # Crear video de prueba
    video_repo = VideoRepository(db_session)
    video = Video(
        source_id=sample_source.id,
        youtube_id="fail_trans_123",  # Max 20 chars
        title="Fail Transcription Test",
        url="https://youtube.com/watch?v=test",
        duration_seconds=300,
        status=VideoStatus.PENDING,
    )
    created_video = video_repo.create(video)
    db_session.commit()

    # Configurar servicio
    service = VideoProcessingService()

    # Downloader funciona
    mock_audio_path = MagicMock(spec=Path)
    mock_audio_path.stat.return_value = MagicMock(st_size=1024 * 1024 * 3)
    mock_audio_path.exists.return_value = True

    service.downloader.download_audio = AsyncMock(return_value=mock_audio_path)

    # Transcriber falla
    service.transcriber.transcribe_audio = AsyncMock(
        side_effect=TranscriptionFailedError("Whisper OOM")
    )

    # Ejecutar pipeline (debe fallar)
    with pytest.raises(TranscriptionFailedError):
        await service.process_video(db_session, created_video.id)

    # Refrescar video desde BD
    db_session.refresh(created_video)

    # Verificar estado final
    assert created_video.status == VideoStatus.FAILED

    # Verificar que downloader SÍ se llamó
    service.downloader.download_audio.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_process_video_summarization_failure_preserves_transcription(
    db_session,
    sample_source,
):
    """
    Test: Fallo en resumen preserva la transcripción en BD.

    Verifica que si falla DeepSeek API, la transcripción (que es costosa)
    se mantiene en BD para poder re-intentar el resumen después.
    """
    # Crear video de prueba
    video_repo = VideoRepository(db_session)
    video = Video(
        source_id=sample_source.id,
        youtube_id="fail_summary_test",
        title="Fail Summary Test",
        url="https://youtube.com/watch?v=test",
        duration_seconds=300,
        status=VideoStatus.PENDING,
    )
    created_video = video_repo.create(video)
    db_session.commit()

    # Configurar servicio
    service = VideoProcessingService()

    # Downloader y transcriber funcionan
    mock_audio_path = MagicMock(spec=Path)
    mock_audio_path.stat.return_value = MagicMock(st_size=1024 * 1024 * 4)
    mock_audio_path.exists.return_value = True

    service.downloader.download_audio = AsyncMock(return_value=mock_audio_path)

    service.transcriber.transcribe_audio = AsyncMock(
        return_value=TranscriptionResult(
            text="This transcription should be preserved even if summary fails.",
            language="en",
            duration=300.0,
        )
    )

    # Summarizer falla
    service.summarizer.generate_summary = AsyncMock(
        side_effect=DeepSeekAPIError("API rate limit", status_code=429)
    )

    # Mock cleanup
    with patch.object(service, "_cleanup_audio_file"):
        # Ejecutar pipeline (debe fallar)
        with pytest.raises(DeepSeekAPIError):
            await service.process_video(db_session, created_video.id)

        # Refrescar video desde BD
        db_session.refresh(created_video)

        # Verificar estado final
        assert created_video.status == VideoStatus.FAILED

        # IMPORTANTE: Verificar que la transcripción SÍ se guardó
        trans_repo = TranscriptionRepository(db_session)
        transcription = trans_repo.get_by_video_id(created_video.id)
        assert transcription is not None
        assert transcription.text == "This transcription should be preserved even if summary fails."

        # Verificar que NO hay resumen (falló antes de crearlo)
        summary_repo = SummaryRepository(db_session)
        summary = summary_repo.get_by_transcription_id(transcription.id)
        assert summary is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_process_video_cannot_reprocess_completed(
    db_session,
    sample_source,
):
    """
    Test: No se puede reprocesar un video en estado COMPLETED.
    """
    # Crear video ya completado
    video_repo = VideoRepository(db_session)
    video = Video(
        source_id=sample_source.id,
        youtube_id="completed_test",
        title="Completed Test",
        url="https://youtube.com/watch?v=test",
        duration_seconds=300,
        status=VideoStatus.COMPLETED,  # Ya completado
    )
    created_video = video_repo.create(video)
    db_session.commit()

    # Crear servicio
    service = VideoProcessingService()

    # Intentar procesar (debe fallar con InvalidVideoStateError)
    with pytest.raises(InvalidVideoStateError) as exc_info:
        await service.process_video(db_session, created_video.id)

    assert "completed" in str(exc_info.value).lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_process_video_can_retry_failed(
    db_session,
    sample_source,
):
    """
    Test: Se puede reintentar un video en estado FAILED.
    """
    # Crear video en estado FAILED
    video_repo = VideoRepository(db_session)
    video = Video(
        source_id=sample_source.id,
        youtube_id="retry_test",
        title="Retry Test",
        url="https://youtube.com/watch?v=test",
        duration_seconds=300,
        status=VideoStatus.FAILED,  # Previamente falló
    )
    created_video = video_repo.create(video)
    db_session.commit()

    # Configurar servicio con mocks exitosos
    service = VideoProcessingService()

    mock_audio_path = MagicMock(spec=Path)
    mock_audio_path.stat.return_value = MagicMock(st_size=1024 * 1024 * 3)
    mock_audio_path.exists.return_value = True

    service.downloader.download_audio = AsyncMock(return_value=mock_audio_path)

    service.transcriber.transcribe_audio = AsyncMock(
        return_value=TranscriptionResult(
            text="Retry successful",
            language="en",
            duration=300.0,
        )
    )

    async def mock_generate_summary(session, transcription_id):
        summary = Summary(
            transcription_id=transcription_id,
            summary_text="Retry summary",
            keywords=["retry"],
            category="concept",
            model_used="deepseek-chat",
            tokens_used=100,
        )
        summary_repo = SummaryRepository(session)
        created_summary = summary_repo.create(summary)
        session.commit()
        return created_summary

    service.summarizer.generate_summary = mock_generate_summary

    # Mock cleanup
    with patch.object(service, "_cleanup_audio_file"):
        # Ejecutar pipeline (ahora debe funcionar)
        result_video = await service.process_video(db_session, created_video.id)

        # Verificar que se completó
        assert result_video.status == VideoStatus.COMPLETED

        # Verificar que se creó transcripción y resumen
        trans_repo = TranscriptionRepository(db_session)
        transcription = trans_repo.get_by_video_id(created_video.id)
        assert transcription is not None

        summary_repo = SummaryRepository(db_session)
        summary = summary_repo.get_by_transcription_id(transcription.id)
        assert summary is not None
