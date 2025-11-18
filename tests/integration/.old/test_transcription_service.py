"""
Tests de integración para TranscriptionService.

Estos tests usan el modelo Whisper real, por lo que:
- La primera ejecución descargará el modelo (~140MB)
- Cada test puede tardar 30-60 segundos
- Requiere archivos de audio reales para probar
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.services.transcription_service import (
    AudioFileNotFoundError,
    InvalidAudioFormatError,
    TranscriptionFailedError,
    TranscriptionResult,
    TranscriptionService,
    get_transcription_service,
)

# === FIXTURES ===


@pytest.fixture
def transcription_service() -> TranscriptionService:
    """
    Fixture que proporciona una instancia del servicio de transcripción.

    Usa el modelo 'base' por defecto.
    """
    return TranscriptionService(model_size="base")


@pytest.fixture
def temp_audio_dir():
    """
    Fixture que crea un directorio temporal para archivos de audio de prueba.

    El directorio se elimina automáticamente al finalizar el test.
    """
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
async def sample_audio_file(temp_audio_dir: Path) -> Path:  # type: ignore
    """
    Fixture que descarga un audio de prueba real usando el downloader_service.

    Esto permite probar la integración entre downloader y transcription.
    Usa un video corto (30s) para que los tests sean rápidos.
    """
    from src.services.downloader_service import DownloaderService

    # URL de video corto de prueba en español (~30 segundos)
    # "Me at the zoo" - primer video de YouTube (19s)
    test_video_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

    downloader = DownloaderService()

    try:
        # Descargar audio
        audio_path = await downloader.download_audio(test_video_url)
        yield audio_path  # type: ignore
    finally:
        # Limpieza: eliminar archivo descargado
        if audio_path.exists():
            audio_path.unlink()


# === TESTS DE FUNCIONALIDAD PRINCIPAL ===


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_audio_success(
    transcription_service: TranscriptionService, sample_audio_file: Path
):
    """
    Test: Transcribir audio exitosamente debe retornar texto válido.

    Valida:
    - El texto no está vacío
    - Se detecta un idioma
    - La duración es mayor a 0
    - El resultado tiene el formato correcto
    """
    # Act
    result = await transcription_service.transcribe_audio(
        audio_path=sample_audio_file, language="en"  # El video de prueba está en inglés
    )

    # Assert
    assert isinstance(result, TranscriptionResult)
    assert len(result.text) > 0, "El texto transcrito no debe estar vacío"
    assert result.language in ["en", "es"], f"Idioma detectado: {result.language}"
    assert result.duration > 0, "La duración debe ser mayor a 0"
    assert result.segments is None, "Por defecto no debe incluir segmentos"

    # Logging para debugging
    print(f"\n📝 Texto transcrito ({len(result.text)} caracteres):")
    print(f"   {result.text[:100]}...")
    print(f"🌍 Idioma: {result.language}")
    print(f"⏱️  Duración: {result.duration:.2f}s")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_with_timestamps_success(
    transcription_service: TranscriptionService, sample_audio_file: Path
):
    """
    Test: Transcribir con timestamps debe retornar segmentos.

    Valida:
    - El texto completo está presente
    - Los segmentos no están vacíos
    - Cada segmento tiene start, end y text
    - Los timestamps son coherentes (end > start)
    """
    # Act
    result = await transcription_service.transcribe_with_timestamps(
        audio_path=sample_audio_file, language="en"
    )

    # Assert
    assert isinstance(result, TranscriptionResult)
    assert len(result.text) > 0
    assert result.segments is not None, "Debe incluir segmentos"
    assert len(result.segments) > 0, "Debe haber al menos un segmento"

    # Validar estructura de segmentos
    for segment in result.segments:
        assert segment.start >= 0, "El tiempo de inicio debe ser >= 0"
        assert segment.end > segment.start, "El fin debe ser mayor que el inicio"
        assert len(segment.text.strip()) > 0, "El texto del segmento no debe estar vacío"

    # Logging
    print(f"\n📝 Transcripción con {len(result.segments)} segmentos:")
    for _i, seg in enumerate(result.segments[:3]):  # Mostrar primeros 3
        print(f"   [{seg.start:.2f}s - {seg.end:.2f}s]: {seg.text[:50]}...")


# === TESTS DE MANEJO DE ERRORES ===


@pytest.mark.asyncio
async def test_audio_file_not_found_raises_error(transcription_service: TranscriptionService):
    """
    Test: Intentar transcribir un archivo que no existe debe lanzar AudioFileNotFoundError.
    """
    non_existent_file = Path("/tmp/audio_que_no_existe_12345.mp3")

    with pytest.raises(AudioFileNotFoundError) as exc_info:
        await transcription_service.transcribe_audio(non_existent_file)

    assert "no encontrado" in str(exc_info.value).lower()
    print(f"\n✅ Error capturado correctamente: {exc_info.value}")


@pytest.mark.asyncio
async def test_invalid_audio_format_raises_error(
    transcription_service: TranscriptionService, temp_audio_dir: Path
):
    """
    Test: Intentar transcribir un archivo con formato no soportado debe fallar.
    """
    # Crear un archivo con extensión no soportada
    invalid_file = temp_audio_dir / "test_audio.txt"
    invalid_file.write_text("Este no es un archivo de audio")

    with pytest.raises(InvalidAudioFormatError) as exc_info:
        await transcription_service.transcribe_audio(invalid_file)

    assert "formato" in str(exc_info.value).lower()
    print(f"\n✅ Error de formato capturado: {exc_info.value}")


@pytest.mark.asyncio
async def test_empty_audio_file_fails_gracefully(
    transcription_service: TranscriptionService, temp_audio_dir: Path
):
    """
    Test: Un archivo MP3 vacío o corrupto debe manejar el error.

    Nota: Whisper puede lanzar diferentes errores dependiendo del archivo,
    así que capturamos Exception genérica pero verificamos que falla.
    """
    # Crear archivo MP3 vacío (corrupto)
    empty_file = temp_audio_dir / "empty.mp3"
    empty_file.write_bytes(b"")

    # Debe fallar (puede ser TranscriptionFailedError o Exception)
    with pytest.raises((TranscriptionFailedError, Exception)) as exc_info:
        await transcription_service.transcribe_audio(empty_file)

    print(f"\n✅ Archivo corrupto manejado: {type(exc_info.value).__name__}")


# === TESTS DE PATRÓN SINGLETON ===


def test_get_transcription_service_returns_singleton():
    """
    Test: get_transcription_service() debe retornar siempre la misma instancia.

    Esto es crítico para evitar cargar el modelo Whisper múltiples veces.
    """
    # Act
    service1 = get_transcription_service()
    service2 = get_transcription_service()

    # Assert
    assert service1 is service2, "Debe retornar la misma instancia (singleton)"
    print("\n✅ Patrón singleton funcionando correctamente")


def test_singleton_model_loaded_only_once():
    """
    Test: El modelo Whisper solo debe cargarse una vez.

    Verifica que después de la primera transcripción, el modelo queda cargado.
    """
    service = get_transcription_service()

    # Forzar carga del modelo
    _ = service._load_model()

    # El modelo ahora debe estar cargado
    assert service._model is not None, "El modelo debe estar cargado"

    # Llamar nuevamente no debe recargar
    model_instance = service._load_model()
    assert model_instance is service._model, "No debe recargar el modelo"

    print("\n✅ Modelo cargado una sola vez (lazy loading OK)")


# === HELPER PARA TESTING MANUAL ===


async def manual_test_transcription(audio_path: str):
    """
    Helper para probar transcripción manualmente desde terminal.

    Uso:
        poetry run python -c "
        import asyncio
        from tests.integration.test_transcription_service import manual_test_transcription
        asyncio.run(manual_test_transcription('/ruta/al/audio.mp3'))
        "

    Args:
        audio_path: Ruta al archivo de audio local
    """
    service = get_transcription_service()

    print(f"\n🎙️  Transcribiendo: {audio_path}")
    print("⏳ Esto puede tardar ~30-60 segundos...")

    try:
        result = await service.transcribe_with_timestamps(
            audio_path=Path(audio_path), language="es"  # Cambia según tu audio
        )

        print("\n✅ Transcripción completada!")
        print(f"📝 Texto ({len(result.text)} caracteres):")
        print(f"   {result.text}\n")
        print(f"🌍 Idioma detectado: {result.language}")
        print(f"⏱️  Duración: {result.duration:.2f}s")
        print(f"📊 Segmentos: {len(result.segments or [])}")

        if result.segments:
            print("\n📍 Primeros 3 segmentos:")
            for seg in result.segments[:3]:
                print(f"   [{seg.start:.2f}s - {seg.end:.2f}s]: {seg.text}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


# Para ejecutar todos los tests:
# poetry run pytest tests/integration/test_transcription_service.py -v -s
