"""
Tests unitarios para TranscriptionService.

Estrategia de testing:
- Mock de whisper.load_model para evitar cargar modelo real
- Uso de tmp_path fixture para archivos de audio temporales
- Validación de estructura de datos retornados
- Manejo de errores (archivos no encontrados, formatos inválidos)
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.transcription_service import (
    AudioFileNotFoundError,
    InvalidAudioFormatError,
    ModelLoadError,
    TranscriptionFailedError,
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionService,
)


class TestTranscriptionServiceValidation:
    """Tests para validación de archivos de audio."""

    @pytest.fixture
    def service(self):
        """Fixture que crea una instancia del servicio."""
        return TranscriptionService()

    def test_validate_audio_file_valid_mp3(self, service, tmp_path):
        """Test 1: Archivo MP3 válido no lanza excepción"""
        # Arrange
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        # Act & Assert - no debe lanzar excepción
        service._validate_audio_file(audio_file)

    def test_validate_audio_file_valid_wav(self, service, tmp_path):
        """Test 2: Archivo WAV válido no lanza excepción"""
        # Arrange
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        # Act & Assert - no debe lanzar excepción
        service._validate_audio_file(audio_file)

    def test_validate_audio_file_not_found(self, service, tmp_path):
        """Test 3: Archivo no existente lanza AudioFileNotFoundError"""
        # Arrange
        non_existent_file = tmp_path / "nonexistent.mp3"

        # Act & Assert
        with pytest.raises(AudioFileNotFoundError, match="no encontrado"):
            service._validate_audio_file(non_existent_file)

    def test_validate_audio_file_invalid_format(self, service, tmp_path):
        """Test 4: Formato inválido lanza InvalidAudioFormatError"""
        # Arrange
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("not an audio file")

        # Act & Assert
        with pytest.raises(InvalidAudioFormatError, match="Formato no soportado"):
            service._validate_audio_file(invalid_file)


class TestTranscriptionServiceModelLoading:
    """Tests para carga del modelo Whisper."""

    def test_model_loads_lazily(self):
        """Test 5: Modelo se carga de forma lazy (no al instanciar)"""
        # Act
        service = TranscriptionService(model_size="base")

        # Assert
        assert service._model is None  # No cargado aún
        assert service.model_size == "base"

    def test_model_loads_on_first_use(self):
        """Test 6: Modelo se carga en primera llamada a _load_model"""
        # Arrange
        service = TranscriptionService(model_size="tiny")

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model

            # Act
            result = service._load_model()

            # Assert
            assert result == mock_model
            assert service._model == mock_model
            mock_load.assert_called_once_with("tiny")

    def test_model_cached_on_subsequent_calls(self):
        """Test 7: Modelo se cachea y no se recarga"""
        # Arrange
        service = TranscriptionService()

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model

            # Act
            result1 = service._load_model()
            result2 = service._load_model()

            # Assert
            assert result1 == result2 == mock_model
            mock_load.assert_called_once()  # Solo se llamó 1 vez

    def test_model_load_failure_raises_error(self):
        """Test 8: Fallo al cargar modelo lanza ModelLoadError"""
        # Arrange
        service = TranscriptionService()

        with patch("whisper.load_model") as mock_load:
            mock_load.side_effect = Exception("Model download failed")

            # Act & Assert
            with pytest.raises(ModelLoadError, match="Error al cargar modelo"):
                service._load_model()


class TestTranscriptionServiceTranscribe:
    """Tests para transcripción de audio."""

    @pytest.fixture
    def service(self):
        return TranscriptionService()

    @pytest.fixture
    def sample_whisper_result(self):
        """Fixture con resultado de Whisper de ejemplo."""
        return {
            "text": "Este es un texto de prueba transcrito por Whisper.",
            "language": "es",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Este es un texto"},
                {"start": 2.5, "end": 5.0, "text": "de prueba transcrito por Whisper."},
            ],
        }

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, service, tmp_path, sample_whisper_result):
        """Test 9: Transcripción exitosa de audio"""
        # Arrange
        audio_file = tmp_path / "test_audio.mp3"
        audio_file.write_bytes(b"fake audio data")

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            mock_model.transcribe.return_value = sample_whisper_result

            # Act
            result = await service.transcribe_audio(audio_file)

            # Assert
            assert isinstance(result, TranscriptionResult)
            assert result.text == "Este es un texto de prueba transcrito por Whisper."
            assert result.language == "es"
            assert result.duration == 5.0  # Última posición end
            assert result.segments is None  # No se pidieron timestamps
            mock_model.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_not_found(self, service, tmp_path):
        """Test 10: Archivo no existente lanza AudioFileNotFoundError"""
        # Arrange
        non_existent_file = tmp_path / "nonexistent_audio.mp3"

        # Act & Assert
        with pytest.raises(AudioFileNotFoundError):
            await service.transcribe_audio(non_existent_file)

    @pytest.mark.asyncio
    async def test_transcribe_audio_invalid_format(self, service, tmp_path):
        """Test 11: Formato inválido lanza InvalidAudioFormatError"""
        # Arrange
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("not an audio file")

        # Act & Assert
        with pytest.raises(InvalidAudioFormatError):
            await service.transcribe_audio(invalid_file)

    @pytest.mark.asyncio
    async def test_transcribe_audio_whisper_failure(self, service, tmp_path):
        """Test 12: Fallo en Whisper lanza TranscriptionFailedError"""
        # Arrange
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            mock_model.transcribe.side_effect = Exception("Whisper processing error")

            # Act & Assert
            with pytest.raises(TranscriptionFailedError, match="Fallo en transcripción"):
                await service.transcribe_audio(audio_file)

    @pytest.mark.asyncio
    async def test_transcribe_audio_custom_language(self, service, tmp_path, sample_whisper_result):
        """Test 13: Idioma personalizado se pasa a Whisper"""
        # Arrange
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            mock_model.transcribe.return_value = sample_whisper_result

            # Act
            await service.transcribe_audio(audio_file, language="en")

            # Assert
            call_args = mock_model.transcribe.call_args
            assert call_args[1]["language"] == "en"

    @pytest.mark.asyncio
    async def test_transcribe_audio_no_segments(self, service, tmp_path):
        """Test 14: Manejo correcto cuando no hay segmentos"""
        # Arrange
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        result_without_segments = {
            "text": "Test transcription",
            "language": "en",
            # Sin campo 'segments'
        }

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            mock_model.transcribe.return_value = result_without_segments

            # Act
            result = await service.transcribe_audio(audio_file)

            # Assert
            assert result.text == "Test transcription"
            assert result.duration == 0.0  # Sin segmentos, duración 0


class TestTranscriptionServiceWithTimestamps:
    """Tests para transcripción con timestamps."""

    @pytest.fixture
    def service(self):
        return TranscriptionService()

    @pytest.fixture
    def sample_whisper_result(self):
        return {
            "text": "Hola mundo. Esto es una prueba.",
            "language": "es",
            "segments": [
                {"start": 0.0, "end": 1.5, "text": " Hola mundo."},
                {"start": 1.5, "end": 3.0, "text": " Esto es una prueba."},
            ],
        }

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps_success(
        self, service, tmp_path, sample_whisper_result
    ):
        """Test 15: Transcripción con timestamps exitosa"""
        # Arrange
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            mock_model.transcribe.return_value = sample_whisper_result

            # Act
            result = await service.transcribe_with_timestamps(audio_file)

            # Assert
            assert isinstance(result, TranscriptionResult)
            assert result.text == "Hola mundo. Esto es una prueba."
            assert result.language == "es"
            assert result.duration == 3.0
            assert result.segments is not None
            assert len(result.segments) == 2

            # Verificar primer segmento
            assert isinstance(result.segments[0], TranscriptionSegment)
            assert result.segments[0].start == 0.0
            assert result.segments[0].end == 1.5
            assert result.segments[0].text == "Hola mundo."

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps_file_not_found(self, service, tmp_path):
        """Test 16: Archivo no existente lanza AudioFileNotFoundError"""
        # Arrange
        non_existent_file = tmp_path / "nonexistent.mp3"

        # Act & Assert
        with pytest.raises(AudioFileNotFoundError):
            await service.transcribe_with_timestamps(non_existent_file)

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps_whisper_failure(self, service, tmp_path):
        """Test 17: Fallo en Whisper lanza TranscriptionFailedError"""
        # Arrange
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            mock_model.transcribe.side_effect = RuntimeError("Whisper crashed")

            # Act & Assert
            with pytest.raises(TranscriptionFailedError, match="Fallo en transcripción"):
                await service.transcribe_with_timestamps(audio_file)

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps_empty_segments(self, service, tmp_path):
        """Test 18: Manejo correcto de lista vacía de segmentos"""
        # Arrange
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        result_empty_segments = {
            "text": "Short text",
            "language": "en",
            "segments": [],  # Lista vacía
        }

        with patch("whisper.load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            mock_model.transcribe.return_value = result_empty_segments

            # Act
            result = await service.transcribe_with_timestamps(audio_file)

            # Assert
            assert result.text == "Short text"
            assert result.segments == []
            assert result.duration == 0.0
