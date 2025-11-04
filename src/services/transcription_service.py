"""
Servicio de transcripción de audio usando OpenAI Whisper.

Este módulo proporciona funcionalidad para transcribir archivos de audio
a texto usando el modelo Whisper ejecutado localmente.
"""

import logging
from pathlib import Path
from typing import Any

import whisper
from pydantic import BaseModel, Field
from whisper import Whisper

# === CONFIGURACIÓN ===

# Modelo Whisper a usar: "tiny", "base", "small", "medium", "large"
# "base" es un buen balance entre velocidad y precisión
DEFAULT_MODEL_SIZE = "base"

# Idioma por defecto para optimizar transcripción
DEFAULT_LANGUAGE = "es"

# Formatos de audio soportados por Whisper
SUPPORTED_FORMATS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac"}

# Logger
logger = logging.getLogger(__name__)


# === EXCEPCIONES PERSONALIZADAS ===


class TranscriptionError(Exception):
    """Excepción base para errores de transcripción."""

    pass


class AudioFileNotFoundError(TranscriptionError):
    """El archivo de audio no existe."""

    pass


class InvalidAudioFormatError(TranscriptionError):
    """El formato del archivo de audio no es válido."""

    pass


class ModelLoadError(TranscriptionError):
    """Error al cargar el modelo Whisper."""

    pass


class TranscriptionFailedError(TranscriptionError):
    """La transcripción falló por razones técnicas."""

    pass


# === MODELOS PYDANTIC ===


class TranscriptionSegment(BaseModel):
    """
    Segmento individual de transcripción con timestamps.

    Útil para crear subtítulos o buscar en partes específicas del audio.
    """

    start: float = Field(..., description="Tiempo de inicio en segundos")
    end: float = Field(..., description="Tiempo de fin en segundos")
    text: str = Field(..., description="Texto transcrito del segmento")


class TranscriptionResult(BaseModel):
    """
    Resultado completo de una transcripción.

    Attributes:
        text: Transcripción completa en texto plano
        language: Idioma detectado (código ISO 639-1)
        duration: Duración del audio en segundos
        segments: Lista de segmentos con timestamps (opcional)
    """

    text: str = Field(..., description="Texto transcrito completo")
    language: str = Field(..., description="Idioma detectado (ej: 'es', 'en')")
    duration: float = Field(..., description="Duración del audio en segundos")
    segments: list[TranscriptionSegment] | None = Field(
        default=None, description="Segmentos con timestamps si se solicitaron"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hola, este es un ejemplo de transcripción.",
                "language": "es",
                "duration": 3.5,
                "segments": [
                    {"start": 0.0, "end": 3.5, "text": "Hola, este es un ejemplo de transcripción."}
                ],
            }
        }


# === SERVICIO DE TRANSCRIPCIÓN ===


class TranscriptionService:
    """
    Servicio para transcribir audio usando OpenAI Whisper.

    El modelo se carga de forma lazy (solo cuando se usa por primera vez)
    para optimizar recursos.

    Examples:
        >>> service = TranscriptionService()
        >>> result = await service.transcribe_audio(Path("audio.mp3"))
        >>> print(result.text)
        'Texto transcrito del audio...'
    """

    def __init__(self, model_size: str = DEFAULT_MODEL_SIZE):
        """
        Inicializa el servicio de transcripción.

        Args:
            model_size: Tamaño del modelo Whisper a usar.
                       Opciones: "tiny", "base", "small", "medium", "large"
                       Por defecto: "base" (74M parámetros)
        """
        self.model_size = model_size
        self._model: Whisper | None = None
        logger.info(f"TranscriptionService inicializado con modelo '{model_size}'")

    def _load_model(self) -> Whisper:
        """
        Carga el modelo Whisper si aún no está cargado (lazy loading).

        Returns:
            Modelo Whisper listo para usar

        Raises:
            ModelLoadError: Si falla la carga del modelo
        """
        if self._model is None:
            try:
                logger.info(f"Cargando modelo Whisper '{self.model_size}'...")
                self._model = whisper.load_model(self.model_size)
                logger.info("Modelo Whisper cargado exitosamente")
            except Exception as e:
                raise ModelLoadError(f"Error al cargar modelo Whisper: {e}") from e

        return self._model

    def _validate_audio_file(self, audio_path: Path) -> None:
        """
        Valida que el archivo de audio existe y tiene formato soportado.

        Args:
            audio_path: Ruta al archivo de audio

        Raises:
            AudioFileNotFoundError: Si el archivo no existe
            InvalidAudioFormatError: Si el formato no es soportado
        """
        if not audio_path.exists():
            raise AudioFileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

        if audio_path.suffix.lower() not in SUPPORTED_FORMATS:
            raise InvalidAudioFormatError(
                f"Formato no soportado: {audio_path.suffix}. "
                f"Formatos válidos: {', '.join(SUPPORTED_FORMATS)}"
            )

        logger.debug(f"Archivo de audio validado: {audio_path}")

    async def transcribe_audio(
        self,
        audio_path: Path,
        language: str = DEFAULT_LANGUAGE,
    ) -> TranscriptionResult:
        """
        Transcribe un archivo de audio a texto.

        Args:
            audio_path: Ruta al archivo de audio (MP3, WAV, etc.)
            language: Código ISO 639-1 del idioma (ej: 'es', 'en')
                     Optimiza la transcripción para ese idioma

        Returns:
            Resultado de transcripción con texto, idioma y duración

        Raises:
            AudioFileNotFoundError: Si el archivo no existe
            InvalidAudioFormatError: Si el formato no es válido
            TranscriptionFailedError: Si la transcripción falla

        Example:
            >>> service = TranscriptionService()
            >>> result = await service.transcribe_audio(
            ...     Path("audio.mp3"),
            ...     language="es"
            ... )
            >>> print(result.text)
        """
        # Validar archivo
        self._validate_audio_file(audio_path)

        # Cargar modelo (lazy)
        model = self._load_model()

        try:
            logger.info(f"Iniciando transcripción de: {audio_path}")

            # Transcribir con Whisper
            result: dict[str, Any] = model.transcribe(
                str(audio_path),
                language=language,
                fp16=False,  # Desactivar FP16 (compatibilidad CPU)
            )

            # Extraer información
            transcribed_text: str = str(result["text"]).strip()
            detected_language: str = str(result.get("language", language))

            # Calcular duración aproximada del audio
            # Whisper no retorna duración directa, la extraemos de los segmentos
            duration = 0.0
            if "segments" in result and result["segments"]:
                last_segment: dict[str, Any] = result["segments"][-1]
                duration = float(last_segment.get("end", 0.0))

            logger.info(
                f"Transcripción completada: {len(transcribed_text)} caracteres, "
                f"idioma: {detected_language}, duración: {duration:.2f}s"
            )

            return TranscriptionResult(
                text=transcribed_text,
                language=detected_language,
                duration=duration,
            )

        except Exception as e:
            logger.error(f"Error durante transcripción: {e}")
            raise TranscriptionFailedError(f"Fallo en transcripción: {e}") from e

    async def transcribe_with_timestamps(
        self,
        audio_path: Path,
        language: str = DEFAULT_LANGUAGE,
    ) -> TranscriptionResult:
        """
        Transcribe audio con timestamps por segmento.

        Útil para crear subtítulos o buscar en partes específicas.

        Args:
            audio_path: Ruta al archivo de audio
            language: Código ISO del idioma

        Returns:
            Resultado con texto completo y lista de segmentos con timestamps

        Raises:
            AudioFileNotFoundError: Si el archivo no existe
            InvalidAudioFormatError: Si el formato no es válido
            TranscriptionFailedError: Si la transcripción falla
        """
        # Validar archivo
        self._validate_audio_file(audio_path)

        # Cargar modelo
        model = self._load_model()

        try:
            logger.info(f"Transcribiendo con timestamps: {audio_path}")

            # Transcribir
            result: dict[str, Any] = model.transcribe(
                str(audio_path),
                language=language,
                fp16=False,
            )

            # Extraer texto completo
            transcribed_text: str = str(result["text"]).strip()
            detected_language: str = str(result.get("language", language))

            # Extraer segmentos con timestamps
            segments: list[TranscriptionSegment] = []
            duration = 0.0

            if "segments" in result:
                for seg in result["segments"]:
                    seg_dict: dict[str, Any] = seg
                    segments.append(
                        TranscriptionSegment(
                            start=float(seg_dict["start"]),
                            end=float(seg_dict["end"]),
                            text=str(seg_dict["text"]).strip(),
                        )
                    )
                    duration = max(duration, float(seg_dict["end"]))

            logger.info(
                f"Transcripción con timestamps completada: "
                f"{len(segments)} segmentos, duración: {duration:.2f}s"
            )

            return TranscriptionResult(
                text=transcribed_text,
                language=detected_language,
                duration=duration,
                segments=segments,
            )

        except Exception as e:
            logger.error(f"Error durante transcripción con timestamps: {e}")
            raise TranscriptionFailedError(f"Fallo en transcripción: {e}") from e


# === INSTANCIA SINGLETON ===

# Instancia global del servicio (modelo se carga lazy)
_transcription_service: TranscriptionService | None = None


def get_transcription_service(model_size: str = DEFAULT_MODEL_SIZE) -> TranscriptionService:
    """
    Obtiene la instancia singleton del servicio de transcripción.

    El modelo se carga solo una vez y se reutiliza en todas las llamadas.

    Args:
        model_size: Tamaño del modelo (solo se usa en primera llamada)

    Returns:
        Instancia del servicio de transcripción

    Example:
        >>> service = get_transcription_service()
        >>> result = await service.transcribe_audio(Path("audio.mp3"))
    """
    global _transcription_service

    if _transcription_service is None:
        _transcription_service = TranscriptionService(model_size=model_size)
        logger.info("Instancia singleton de TranscriptionService creada")

    return _transcription_service
