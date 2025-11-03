"""
Servicio de descarga de audio de YouTube usando yt-dlp.

Este módulo encapsula la lógica para:
- Descargar audio de videos de YouTube en formato MP3
- Extraer metadata (título, duración, autor) sin descargar
- Manejo robusto de errores (videos privados, URLs inválidas, timeouts)

Requiere FFmpeg instalado en el sistema para conversión de audio.
"""

import re
from pathlib import Path
from typing import Any

import yt_dlp
from pydantic import BaseModel, Field
from yt_dlp.utils import DownloadError as YtDlpDownloadError

# ==================== CONSTANTES ====================

# Ruta donde se guardarán los archivos descargados
# /tmp/ se limpia automáticamente en Linux
DOWNLOAD_DIR = Path("/tmp/youtube_downloads")

# Timeout máximo para descargas (5 minutos)
DOWNLOAD_TIMEOUT = 300

# Tamaño mínimo esperado de un archivo de audio válido (10KB)
MIN_AUDIO_SIZE = 10 * 1024  # 10 KB en bytes

# Regex para validar URLs de YouTube
YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+(&.*)?$"
)


# ==================== EXCEPCIONES PERSONALIZADAS ====================


class DownloadError(Exception):
    """Excepción base para errores del servicio de descarga."""

    pass


class InvalidURLError(DownloadError):
    """La URL proporcionada no es válida o no es de YouTube."""

    pass


class VideoNotAvailableError(DownloadError):
    """El video no está disponible (privado, eliminado, región bloqueada)."""

    pass


class NetworkError(DownloadError):
    """Error de red durante la descarga (timeout, conexión perdida)."""

    pass


class AudioExtractionError(DownloadError):
    """Error al extraer/convertir el audio a MP3."""

    pass


# ==================== MODELOS DE DATOS ====================


class VideoMetadata(BaseModel):
    """
    Metadata de un video de YouTube.

    Attributes:
        video_id: ID único del video (ej: "dQw4w9WgXcQ").
        title: Título completo del video.
        duration_seconds: Duración en segundos.
        duration_formatted: Duración formateada (ej: "03:45").
        author: Nombre del canal/autor.
        thumbnail_url: URL de la miniatura del video.
        view_count: Número de visualizaciones (puede ser None).
    """

    video_id: str = Field(..., description="ID único del video")
    title: str = Field(..., description="Título del video")
    duration_seconds: int = Field(..., description="Duración en segundos")
    duration_formatted: str = Field(..., description="Duración formateada (MM:SS)")
    author: str = Field(..., description="Nombre del canal")
    thumbnail_url: str = Field(..., description="URL de la miniatura")
    view_count: int | None = Field(None, description="Número de visualizaciones")


# ==================== SERVICIO PRINCIPAL ====================


class DownloaderService:
    """
    Servicio para descargar audio de YouTube y extraer metadata.

    Este servicio usa yt-dlp para:
    1. Validar URLs de YouTube
    2. Descargar audio en formato MP3
    3. Extraer metadata sin descargar el video

    Example:
        >>> service = DownloaderService()
        >>> audio_path = await service.download_audio("https://youtube.com/watch?v=...")
        >>> print(f"Audio descargado: {audio_path}")
    """

    def __init__(self):
        """
        Inicializa el servicio de descarga.

        Crea el directorio de descargas si no existe.
        """
        # Crear directorio de descargas si no existe
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def _validate_youtube_url(self, url: str) -> None:
        """
        Valida que la URL sea de YouTube y esté bien formada.

        Args:
            url: URL a validar.

        Raises:
            InvalidURLError: Si la URL no es válida o no es de YouTube.
        """
        if not url or not isinstance(url, str):
            raise InvalidURLError("La URL no puede estar vacía")

        if not YOUTUBE_URL_PATTERN.match(url):
            raise InvalidURLError("URL inválida. Debe ser youtube.com/watch?v=... o youtu.be/...")

    async def get_video_metadata(self, url: str) -> VideoMetadata:
        """
        Extrae metadata del video sin descargarlo.

        Este método es RÁPIDO porque solo hace una petición HTTP
        para obtener información, sin descargar el video.

        Args:
            url: URL del video de YouTube.

        Returns:
            VideoMetadata con información del video.

        Raises:
            InvalidURLError: URL inválida.
            VideoNotAvailableError: Video no disponible.
            NetworkError: Error de conexión.
        """
        # Validar URL antes de hacer peticiones
        self._validate_youtube_url(url)

        # Configuración de yt-dlp para solo extraer info
        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
                # Extraer información del video
                info = ydl.extract_info(url, download=False)

                if not info:
                    raise VideoNotAvailableError("No se pudo obtener información del video")

                # Formatear duración (segundos -> MM:SS)
                duration_seconds = info.get("duration") or 0
                minutes = duration_seconds // 60
                seconds = duration_seconds % 60
                duration_formatted = f"{minutes:02d}:{seconds:02d}"

                # Validar campos obligatorios
                if "id" not in info or not info["id"]:
                    raise VideoNotAvailableError("El video no tiene ID válido")
                if "title" not in info or not info["title"]:
                    raise VideoNotAvailableError("El video no tiene título válido")

                # Construir modelo de metadata con valores seguros
                return VideoMetadata(
                    video_id=info["id"],
                    title=info["title"],
                    duration_seconds=duration_seconds,
                    duration_formatted=duration_formatted,
                    author=info.get("uploader") or "Desconocido",
                    thumbnail_url=info.get("thumbnail") or "",
                    view_count=info.get("view_count"),
                )

        except YtDlpDownloadError as e:
            error_msg = str(e).lower()

            # Clasificar tipo de error según el mensaje
            if "private" in error_msg or "unavailable" in error_msg:
                raise VideoNotAvailableError(f"Video no disponible: {e}") from e
            elif "network" in error_msg or "timeout" in error_msg:
                raise NetworkError(f"Error de red: {e}") from e
            else:
                raise DownloadError(f"Error al obtener metadata: {e}") from e

        except Exception as e:
            raise DownloadError(f"Error inesperado: {e}") from e

    async def download_audio(self, url: str) -> Path:
        """
        Descarga el audio de un video de YouTube en formato MP3.

        Args:
            url: URL del video de YouTube.

        Returns:
            Path al archivo MP3 descargado.

        Raises:
            InvalidURLError: URL inválida.
            VideoNotAvailableError: Video no disponible.
            NetworkError: Error de conexión.
            AudioExtractionError: Error al extraer/convertir audio.
        """
        # Validar URL
        self._validate_youtube_url(url)

        # Configuración de yt-dlp para descargar audio
        ydl_opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": DOWNLOAD_TIMEOUT,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
                # Descargar y extraer audio
                info = ydl.extract_info(url, download=True)

                if not info:
                    raise VideoNotAvailableError("No se pudo descargar el video")

                # Construir path del archivo MP3 final
                video_id = info["id"]
                audio_path = DOWNLOAD_DIR / f"{video_id}.mp3"

                # Verificar que el archivo existe
                if not audio_path.exists():
                    raise AudioExtractionError(f"El archivo de audio no se generó: {audio_path}")

                # Verificar tamaño mínimo (detectar archivos corruptos)
                file_size = audio_path.stat().st_size
                if file_size < MIN_AUDIO_SIZE:
                    raise AudioExtractionError(
                        f"Archivo de audio demasiado pequeño: {file_size} bytes "
                        f"(mínimo: {MIN_AUDIO_SIZE} bytes)"
                    )

                return audio_path

        except YtDlpDownloadError as e:
            error_msg = str(e).lower()

            if "private" in error_msg or "unavailable" in error_msg:
                raise VideoNotAvailableError(f"Video no disponible: {e}") from e
            elif "network" in error_msg or "timeout" in error_msg:
                raise NetworkError(f"Error de red al descargar: {e}") from e
            elif "ffmpeg" in error_msg:
                raise AudioExtractionError(
                    f"Error al extraer audio (¿FFmpeg instalado?): {e}"
                ) from e
            else:
                raise DownloadError(f"Error al descargar audio: {e}") from e

        except Exception as e:
            raise DownloadError(f"Error inesperado al descargar: {e}") from e
