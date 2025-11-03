"""
Tests de integración para DownloaderService con yt-dlp.

Estos tests realizan descargas REALES de YouTube.
IMPORTANTE: Cada test descarga ~1-5MB de audio.

Ejecutar con:
    pytest tests/integration/test_downloader_service.py -v
"""

from pathlib import Path

import pytest

from src.services.downloader_service import (
    DownloadError,
    DownloaderService,
    InvalidURLError,
    VideoMetadata,
    VideoNotAvailableError,
)

# URL de video público corto de YouTube (test oficial de yt-dlp)
# Video de 30 segundos para tests rápidos
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=Atpj2UsF65M"  # Test video 30s

# URL inválida para tests de error
INVALID_URL = "https://not-youtube.com/watch?v=invalid"

# URL de video privado (para test de error)
PRIVATE_VIDEO_URL = "https://www.youtube.com/watch?v=thisisnotreal123"


# ==================== FIXTURES ====================


@pytest.fixture
def service():
    """Fixture que provee una instancia del servicio."""
    return DownloaderService()


@pytest.fixture
def cleanup_downloads():
    """
    Fixture que limpia archivos descargados después de cada test.

    Yields control al test y luego limpia.
    """
    downloaded_files = []

    def track_file(file_path: Path):
        """Helper para registrar archivos a limpiar."""
        downloaded_files.append(file_path)

    yield track_file

    # Cleanup después del test
    for file_path in downloaded_files:
        if file_path.exists():
            file_path.unlink()


# ==================== TESTS ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_download_audio_success(service, cleanup_downloads):
    """
    Test: Descarga exitosa de audio de YouTube.

    Este es el test más importante: verifica el flujo completo.
    NOTA: Descarga ~2-3MB, puede tardar 5-15 segundos.
    """
    # Descargar audio
    audio_path = await service.download_audio(TEST_VIDEO_URL)
    cleanup_downloads(audio_path)

    # Verificar que el archivo existe
    assert audio_path.exists()
    assert audio_path.suffix == ".mp3"

    # Verificar tamaño mínimo (archivo válido)
    file_size = audio_path.stat().st_size
    assert file_size > 10 * 1024  # >10KB

    # Verificar que está en el directorio correcto
    assert audio_path.parent.name == "youtube_downloads"

    print("\n✅ Audio descargado exitosamente:")
    print(f"   Path: {audio_path}")
    print(f"   Tamaño: {file_size / 1024:.1f} KB")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_metadata_only(service):
    """
    Test: Extracción de metadata sin descargar el video.

    Este test es RÁPIDO porque no descarga nada.
    """
    # Obtener metadata
    metadata = await service.get_video_metadata(TEST_VIDEO_URL)

    # Verificar tipo
    assert isinstance(metadata, VideoMetadata)

    # Verificar campos obligatorios
    assert metadata.video_id is not None
    assert len(metadata.video_id) > 0

    assert metadata.title is not None
    assert len(metadata.title) > 0

    assert metadata.duration_seconds > 0
    assert metadata.duration_formatted is not None

    assert metadata.author is not None
    assert metadata.thumbnail_url is not None

    # Verificar formato de duración (MM:SS)
    assert ":" in metadata.duration_formatted
    parts = metadata.duration_formatted.split(":")
    assert len(parts) == 2
    assert parts[0].isdigit() and parts[1].isdigit()

    print("\n✅ Metadata extraída exitosamente:")
    print(f"   Video ID: {metadata.video_id}")
    print(f"   Título: {metadata.title[:50]}...")
    print(f"   Duración: {metadata.duration_formatted} ({metadata.duration_seconds}s)")
    print(f"   Autor: {metadata.author}")
    print(f"   Vistas: {metadata.view_count}")


@pytest.mark.asyncio
async def test_invalid_url_fails(service):
    """
    Test: URL inválida debe fallar con InvalidURLError.
    """
    with pytest.raises(InvalidURLError) as exc_info:
        await service.download_audio(INVALID_URL)

    assert "inválida" in str(exc_info.value).lower()
    print(f"\n✅ URL inválida detectada correctamente: {exc_info.value}")


@pytest.mark.asyncio
async def test_empty_url_fails(service):
    """
    Test: URL vacía debe fallar.
    """
    with pytest.raises(InvalidURLError):
        await service.download_audio("")


@pytest.mark.asyncio
async def test_private_video_fails(service):
    """
    Test: Video privado/inexistente debe fallar.

    NOTA: Este test puede ser lento si yt-dlp intenta reintentar.
    """
    with pytest.raises((VideoNotAvailableError, DownloadError)):
        await service.download_audio(PRIVATE_VIDEO_URL)

    print("\n✅ Video no disponible detectado correctamente")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_audio_file_format_is_mp3(service, cleanup_downloads):
    """
    Test: El archivo descargado debe ser MP3 válido.
    """
    audio_path = await service.download_audio(TEST_VIDEO_URL)
    cleanup_downloads(audio_path)

    # Verificar extensión
    assert audio_path.suffix == ".mp3"

    # Verificar que el nombre del archivo es el video_id
    assert len(audio_path.stem) == 11  # IDs de YouTube tienen 11 caracteres

    print(f"\n✅ Formato de archivo correcto: {audio_path.name}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_metadata_completeness(service):
    """
    Test: Metadata debe tener todos los campos requeridos.
    """
    metadata = await service.get_video_metadata(TEST_VIDEO_URL)

    # Verificar que ningún campo obligatorio es None o vacío
    assert metadata.video_id
    assert metadata.title
    assert metadata.duration_seconds > 0
    assert metadata.duration_formatted
    assert metadata.author
    assert metadata.thumbnail_url

    # view_count es opcional (puede ser None)

    print("\n✅ Todos los campos de metadata están completos")


# ==================== HELPER PARA PRUEBAS MANUALES ====================


async def manual_test():
    """
    Función helper para probar el servicio manualmente.

    Ejecutar con:
        python -c "import asyncio; from tests.integration.test_downloader_service import manual_test; asyncio.run(manual_test())"
    """
    print("🧪 Iniciando test manual del servicio de descarga...\n")

    service = DownloaderService()

    # Test 1: Obtener metadata
    print(f"📋 Extrayendo metadata de: {TEST_VIDEO_URL}")
    metadata = await service.get_video_metadata(TEST_VIDEO_URL)  # type: ignore[arg-type]

    print("\n✅ Metadata extraída:")
    print(f"   Video ID: {metadata.video_id}")
    print(f"   Título: {metadata.title}")
    print(f"   Duración: {metadata.duration_formatted} ({metadata.duration_seconds}s)")
    print(f"   Autor: {metadata.author}")
    print(f"   Vistas: {metadata.view_count}")

    # Test 2: Descargar audio
    print("\n⏳ Descargando audio (esto puede tardar 10-30 segundos)...")
    audio_path = await service.download_audio(TEST_VIDEO_URL)  # type: ignore[arg-type]

    file_size = audio_path.stat().st_size
    print("\n✅ Audio descargado exitosamente:")
    print(f"   Path: {audio_path}")
    print(f"   Tamaño: {file_size / 1024:.1f} KB")

    # Limpiar archivo descargado
    if audio_path.exists():
        audio_path.unlink()
        print(f"\n🧹 Archivo limpiado: {audio_path.name}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(manual_test())
