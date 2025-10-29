"""
Servicio de resumen de texto usando DeepSeek API.

Este módulo encapsula la lógica de comunicación con DeepSeek para generar
resúmenes automáticos de transcripciones de YouTube usando LLMs.

La API de DeepSeek es síncrona y compatible con el SDK de OpenAI,
lo que simplifica drásticamente el código comparado con APIs job-based.

Características:
- API síncrona (sin polling)
- Context caching automático (descuento 90% en tokens cacheados)
- JSON output estructurado
- Sistema de prompts versionado y mantenible
"""

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.core.config import settings
from src.services.prompts import format_user_prompt, load_prompt

# ==================== CONSTANTES ====================
# Modelo de DeepSeek a usar
MODEL_NAME = "deepseek-chat"

# Timeouts de red (en segundos)
REQUEST_TIMEOUT = 60  # Timeout para la llamada a la API

# Parámetros del modelo
DEFAULT_MAX_TOKENS = 500  # Suficiente para resumen de ~250 palabras
DEFAULT_TEMPERATURE = 0.3  # Baja para respuestas consistentes
DEFAULT_TOP_P = 0.9  # Nucleus sampling


# ==================== EXCEPCIONES PERSONALIZADAS ====================


class SummarizationError(Exception):
    """Excepción base para errores del servicio de resumen."""

    pass


class DeepSeekAPIError(SummarizationError):
    """Error al comunicarse con la API de DeepSeek."""

    def __init__(self, message: str, status_code: int | None = None):
        """
        Inicializa el error con detalles de la petición fallida.

        Args:
            message: Descripción del error.
            status_code: Código HTTP de la respuesta (si aplica).
        """
        self.status_code = status_code
        super().__init__(message)


class InvalidResponseError(SummarizationError):
    """La API devolvió una respuesta con formato inválido."""

    pass


# ==================== MODELOS DE DATOS ====================


class SummarizationResult(BaseModel):
    """
    Resultado final de un resumen completado.

    Attributes:
        summary: Texto resumido generado por el LLM.
        original_length: Longitud del texto original (en caracteres).
        summary_length: Longitud del resumen (en caracteres).
        language: Idioma del resumen generado.
        model_used: Modelo de LLM utilizado.
        tokens_used: Tokens consumidos (prompt + completion).
        cached_tokens: Tokens leídos desde cache (ahorro de costos).
    """

    summary: str = Field(..., description="Texto del resumen generado")
    original_length: int = Field(..., description="Longitud del texto original")
    summary_length: int = Field(..., description="Longitud del resumen")
    language: str = Field(default="Spanish", description="Idioma del resumen")
    model_used: str = Field(..., description="Modelo LLM usado")
    tokens_used: int = Field(..., description="Tokens totales consumidos")
    cached_tokens: int = Field(default=0, description="Tokens cacheados")


# ==================== SERVICIO PRINCIPAL ====================


class SummarizationService:
    """
    Servicio para generar resúmenes de texto usando DeepSeek API.

    Este servicio maneja la comunicación con DeepSeek mediante el SDK de OpenAI,
    incluyendo el sistema de prompts, manejo de errores y cálculo de métricas.

    Attributes:
        _client: Cliente asíncrono de OpenAI (configurado para DeepSeek).
        _system_prompt: Prompt del sistema cargado desde archivo.
    """

    def __init__(self):
        """
        Inicializa el servicio de resúmenes.

        La API key y base URL se cargan automáticamente desde settings.
        """
        self._client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=REQUEST_TIMEOUT,
        )

        # Cargar system prompt al inicializar (se reutiliza en todas las llamadas)
        self._system_prompt = load_prompt("system_prompt.txt")

    async def __aenter__(self):
        """Soporte para context manager (async with)."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra el cliente HTTP al salir del context manager."""
        await self._client.close()

    async def get_summary_result(
        self,
        title: str,
        duration: str,
        transcription: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> SummarizationResult:
        """
        Genera un resumen de una transcripción de vídeo.

        Este es el método principal del servicio. Orquesta la generación del prompt,
        llamada a la API y parseo del resultado.

        Args:
            title: Título del vídeo.
            duration: Duración formateada (ej: "15:30").
            transcription: Texto de la transcripción completa.
            max_tokens: Máximo de tokens a generar (default: 500).
            temperature: Temperatura del modelo (0-2, default: 0.3).

        Returns:
            SummarizationResult con el resumen generado y metadatos.

        Raises:
            DeepSeekAPIError: Si la API devuelve error.
            InvalidResponseError: Si la respuesta tiene formato inválido.

        Example:
            >>> async with SummarizationService() as service:
            ...     result = await service.get_summary_result(
            ...         title="Introducción a FastAPI",
            ...         duration="18:45",
            ...         transcription="En este video vamos a..."
            ...     )
            ...     print(result.summary)
            'Este vídeo presenta los conceptos fundamentales de FastAPI...'
        """
        # Generar user prompt con datos del vídeo
        user_prompt = format_user_prompt(
            title=title,
            duration=duration,
            transcription=transcription,
        )

        try:
            # Llamada a DeepSeek API
            response = await self._client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=DEFAULT_TOP_P,
            )

            # Extraer resultado
            if not response.choices or len(response.choices) == 0:
                raise InvalidResponseError("La API no devolvió ningún choice")

            summary_text = response.choices[0].message.content

            if not summary_text:
                raise InvalidResponseError("El resumen generado está vacío")

            # Extraer métricas de uso
            usage = response.usage
            if not usage:
                raise InvalidResponseError("La respuesta no incluye información de usage")

            # Construir resultado
            return SummarizationResult(
                summary=summary_text.strip(),
                original_length=len(transcription),
                summary_length=len(summary_text),
                language="Spanish",
                model_used=MODEL_NAME,
                tokens_used=usage.total_tokens,
                cached_tokens=getattr(usage, "prompt_cache_hit_tokens", 0),
            )

        except Exception as error:
            # Capturar errores del SDK de OpenAI
            if hasattr(error, "status_code") and hasattr(error, "__dict__"):
                status_code = getattr(error, "status_code", None)
                raise DeepSeekAPIError(
                    f"Error HTTP {status_code}: {str(error)}",
                    status_code=status_code,
                ) from error
            else:
                raise SummarizationError(f"Error inesperado: {error}") from error
