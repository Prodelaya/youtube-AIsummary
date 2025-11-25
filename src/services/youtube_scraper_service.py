"""
Servicio para scraping de metadata de videos de YouTube sin descargar contenido.

Este servicio usa yt-dlp para extraer solo la información de videos de un canal,
sin descargar audio ni video. Es usado por el sistema de scraping automático
para detectar nuevos contenidos.

Uso:
    service = YouTubeScraperService()
    videos = service.get_latest_videos(
        channel_url="https://www.youtube.com/@DotCSV",
        limit=10
    )
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import yt_dlp

from src.core.config import settings

logger = logging.getLogger(__name__)


# ==================== EXCEPCIONES ====================


class YouTubeScraperError(Exception):
    """Error base para el scraper de YouTube."""

    pass


class InvalidChannelURLError(YouTubeScraperError):
    """La URL del canal no es válida o no existe."""

    pass


class ChannelUnavailableError(YouTubeScraperError):
    """El canal está privado, eliminado o no accesible."""

    pass


class RateLimitError(YouTubeScraperError):
    """YouTube está limitando las peticiones (rate limit)."""

    pass


# ==================== DATA MODELS ====================


@dataclass
class VideoMetadata:
    """
    Metadata de un video de YouTube extraída por yt-dlp.

    Atributos:
        video_id: ID único del video en YouTube (ej: 'dQw4w9WgXcQ')
        title: Título del video
        url: URL completa del video
        duration_seconds: Duración en segundos
        published_at: Fecha de publicación (datetime)
        view_count: Número de visualizaciones
        like_count: Número de likes
        channel_name: Nombre del canal
        thumbnail_url: URL de la miniatura
    """

    video_id: str
    title: str
    url: str
    duration_seconds: int
    published_at: datetime
    view_count: int | None = None
    like_count: int | None = None
    channel_name: str | None = None
    thumbnail_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario serializable."""
        return {
            "video_id": self.video_id,
            "title": self.title,
            "url": self.url,
            "duration_seconds": self.duration_seconds,
            "published_at": self.published_at.isoformat(),
            "view_count": self.view_count,
            "like_count": self.like_count,
            "channel_name": self.channel_name,
            "thumbnail_url": self.thumbnail_url,
        }


# ==================== SERVICIO ====================


class YouTubeScraperService:
    """
    Servicio para extraer metadata de videos de YouTube.

    Este servicio NO descarga videos ni audio, solo extrae información
    usando yt-dlp en modo metadata.
    """

    def __init__(self):
        """Inicializa el servicio con configuración de yt-dlp."""
        self.ydl_opts = {
            # Solo extraer metadata, NO descargar
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,  # Necesitamos metadata completa
            "skip_download": True,  # CRÍTICO: no descargar nada
            # Timeouts
            "socket_timeout": 30,
            # Headers para evitar rate limits
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            # Playlist handling
            "playlistend": settings.YOUTUBE_MAX_RESULTS_PER_CHANNEL,
            "ignoreerrors": True,  # Continuar si falla un video individual
            # Logging
            "logger": logger,
        }

    def get_latest_videos(self, channel_url: str, limit: int = 10) -> list[VideoMetadata]:
        """
        Obtiene los últimos N videos de un canal de YouTube.

        Args:
            channel_url: URL del canal (ej: 'https://www.youtube.com/@DotCSV')
            limit: Número máximo de videos a retornar (default: 10)

        Returns:
            Lista de VideoMetadata con la información de los videos.
            Si el canal está vacío o hay error, retorna lista vacía.

        Raises:
            InvalidChannelURLError: Si la URL no es válida
            ChannelUnavailableError: Si el canal no existe o está privado
            RateLimitError: Si YouTube está bloqueando las peticiones

        Example:
            >>> service = YouTubeScraperService()
            >>> videos = service.get_latest_videos(
            ...     "https://www.youtube.com/@DotCSV",
            ...     limit=5
            ... )
            >>> print(f"Se encontraron {len(videos)} videos")
        """
        # Validar URL básica
        if not channel_url or not isinstance(channel_url, str):
            raise InvalidChannelURLError(f"URL inválida: {channel_url}")

        if "youtube.com" not in channel_url and "youtu.be" not in channel_url:
            raise InvalidChannelURLError(f"La URL no es de YouTube: {channel_url}")

        logger.info(f"🔍 Scraping canal: {channel_url} (limit={limit})")

        # Configurar límite para esta petición
        opts = {**self.ydl_opts, "playlistend": limit}

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                # Extraer info del canal/playlist
                info = ydl.extract_info(channel_url, download=False)

                if not info:
                    logger.warning(f"⚠️ No se pudo extraer info de: {channel_url}")
                    return []

                # Si es un canal, yt-dlp retorna una playlist con los videos
                entries = info.get("entries", [])

                if not entries:
                    logger.info(f"📭 Canal vacío o sin videos: {channel_url}")
                    return []

                # Convertir entries a VideoMetadata
                videos: list[VideoMetadata] = []
                for entry in entries:
                    if not entry:  # Entry puede ser None si ignoreerrors=True
                        continue

                    try:
                        video = self._parse_video_entry(entry)
                        videos.append(video)
                    except Exception as e:
                        logger.warning(f"⚠️ Error parseando video {entry.get('id', 'unknown')}: {e}")
                        continue

                logger.info(f"✅ Scrapeados {len(videos)} videos de {channel_url}")
                return videos

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()

            if "private" in error_msg or "unavailable" in error_msg:
                raise ChannelUnavailableError(f"Canal no disponible: {channel_url}") from e

            if "429" in error_msg or "rate" in error_msg:
                raise RateLimitError(f"Rate limit de YouTube alcanzado para: {channel_url}") from e

            # Error genérico
            logger.error(f"❌ Error descargando info de {channel_url}: {e}")
            raise YouTubeScraperError(f"Error al scrapear canal: {channel_url}") from e

        except Exception as e:
            logger.error(f"❌ Error inesperado scrapeando {channel_url}: {e}")
            raise YouTubeScraperError(f"Error inesperado: {channel_url}") from e

    def _parse_video_entry(self, entry: dict[str, Any]) -> VideoMetadata:
        """
        Parsea un entry de yt-dlp a VideoMetadata.

        Args:
            entry: Diccionario con info del video de yt-dlp

        Returns:
            VideoMetadata con los campos parseados

        Raises:
            ValueError: Si faltan campos requeridos
        """
        video_id = entry.get("id")
        if not video_id:
            raise ValueError("Entry sin 'id'")

        title = entry.get("title", "Sin título")
        url = entry.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}"
        duration = entry.get("duration", 0)

        # Parsear fecha de publicación
        upload_date_str = entry.get("upload_date")  # Formato: YYYYMMDD
        if upload_date_str:
            try:
                published_at = datetime.strptime(upload_date_str, "%Y%m%d")
            except ValueError:
                logger.warning(f"⚠️ Fecha inválida para {video_id}: {upload_date_str}")
                published_at = datetime.now()
        else:
            published_at = datetime.now()

        # Campos opcionales
        view_count = entry.get("view_count")
        like_count = entry.get("like_count")
        channel_name = entry.get("channel") or entry.get("uploader")
        thumbnail_url = entry.get("thumbnail")

        return VideoMetadata(
            video_id=video_id,
            title=title,
            url=url,
            duration_seconds=duration,
            published_at=published_at,
            view_count=view_count,
            like_count=like_count,
            channel_name=channel_name,
            thumbnail_url=thumbnail_url,
        )
