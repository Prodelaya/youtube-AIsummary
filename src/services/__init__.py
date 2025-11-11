"""
Servicios de logica de negocio.

Este modulo expone todos los servicios principales del sistema para
facilitar las importaciones en otros modulos.
"""

# Servicio de descarga de audio de YouTube
from src.services.downloader_service import (
    AudioExtractionError,
    DownloadError,
    DownloaderService,
    InvalidURLError,
    NetworkError,
    VideoMetadata,
    VideoNotAvailableError,
)

# Servicio de resumen con DeepSeek API
from src.services.summarization_service import (
    DeepSeekAPIError,
    InvalidResponseError,
    SummarizationError,
    SummarizationResult,
    SummarizationService,
    categorize_summary,
    extract_keywords,
)

# Servicio de transcripcion con Whisper
from src.services.transcription_service import (
    AudioFileNotFoundError,
    InvalidAudioFormatError,
    ModelLoadError,
    TranscriptionError,
    TranscriptionFailedError,
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionService,
    get_transcription_service,
)

# Servicio orquestador del pipeline completo
from src.services.video_processing_service import (
    InvalidVideoStateError,
    VideoNotFoundError,
    VideoProcessingError,
    VideoProcessingService,
)

# Exportar todo
__all__ = [
    # Downloader
    "DownloaderService",
    "VideoMetadata",
    "DownloadError",
    "InvalidURLError",
    "VideoNotAvailableError",
    "NetworkError",
    "AudioExtractionError",
    # Transcription
    "TranscriptionService",
    "get_transcription_service",
    "TranscriptionResult",
    "TranscriptionSegment",
    "TranscriptionError",
    "AudioFileNotFoundError",
    "InvalidAudioFormatError",
    "ModelLoadError",
    "TranscriptionFailedError",
    # Summarization
    "SummarizationService",
    "SummarizationResult",
    "SummarizationError",
    "DeepSeekAPIError",
    "InvalidResponseError",
    "extract_keywords",
    "categorize_summary",
    # Video Processing (Orquestador)
    "VideoProcessingService",
    "VideoProcessingError",
    "VideoNotFoundError",
    "InvalidVideoStateError",
]
