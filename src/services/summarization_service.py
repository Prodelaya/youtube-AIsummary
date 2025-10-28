"""
Servicio de resumen de texto usando ApyHub AI API.

Este módulo encapsula la lógica de comunicación con ApyHub para generar
resúmenes automáticos de textos largos (como transcripciones de YouTube).

La API de ApyHub funciona de forma asíncrona:
1. Se envía el texto y se recibe un job_id
2. Se consulta periódicamente el estado del job
3. Cuando está completo, se obtiene el resumen generado

Características:
- Reintentos automáticos ante fallos temporales
- Polling inteligente para consultar estado del job
- Configuración flexible de parámetros del resumen
"""

import asyncio
from typing import Any

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings

# ==================== CONSTANTES ====================
# URL base de la API de ApyHub
APYHUB_BASE_URL = "https://api.apyhub.com/sharpapi/api/v1"

# Endpoints específicos
SUMMARIZE_ENDPOINT = f"{APYHUB_BASE_URL}/content/summarize"

# Timeouts de red (en segundos)
REQUEST_TIMEOUT = 30  # Timeout para peticiones HTTP
JOB_TIMEOUT = 300  # Timeout máximo esperando resultado (5 minutos)

# Configuración de polling
POLLING_INTERVAL = 3  # Segundos entre consultas de estado
MAX_POLLING_ATTEMPTS = 100  # Máximo de intentos de consulta

# === LÍMITES DE CUOTA (PLAN GRATUITO: 10 llamadas/día) ===
# IMPORTANTE: Solo submit_summarization_job() consume cuota.
# El polling (check_job_status) NO consume cuota.
MAX_RETRY_ATTEMPTS = 2  # ✅ REDUCIDO: Máximo 2 llamadas por resumen
RETRY_MIN_WAIT = 2  # Segundos de espera mínima entre reintentos
RETRY_MAX_WAIT = 10  # Segundos de espera máxima entre reintentos

# Parámetros por defecto para resúmenes
DEFAULT_VOICE_TONE = "neutral"  # Tono del resumen
DEFAULT_MAX_LENGTH = 250  # Longitud máxima en palabras
DEFAULT_LANGUAGE = "Spanish"  # Idioma del resumen

# === ADVERTENCIA DE USO ===
# Con MAX_RETRY_ATTEMPTS=2:
# - Caso normal: 1 llamada por resumen
# - Caso con fallo temporal: 2 llamadas por resumen
# - Producción: Implementar rate limiter local para no exceder 10/día


# ==================== EXCEPCIONES PERSONALIZADAS ====================


class SummarizationError(Exception):
    """Excepción base para errores del servicio de resumen."""

    pass


class ApyHubAPIError(SummarizationError):
    """Error al comunicarse con la API de ApyHub."""

    def __init__(self, message: str, status_code: int | None = None):
        """
        Inicializa el error con detalles de la petición fallida.

        Args:
            message: Descripción del error.
            status_code: Código HTTP de la respuesta (si aplica).
        """
        self.status_code = status_code
        super().__init__(message)


class SummarizationTimeoutError(SummarizationError):
    """El job de resumen excedió el tiempo máximo de espera."""

    pass


class InvalidResponseError(SummarizationError):
    """La API devolvió una respuesta con formato inválido."""

    pass


# ==================== MODELOS DE DATOS ====================


class SummarizationJob(BaseModel):
    """
    Representa un job de resumen enviado a ApyHub.

    Attributes:
        job_id: Identificador único del job.
        status_url: URL para consultar el estado del job.
    """

    job_id: str = Field(..., description="ID único del job de resumen")
    status_url: str = Field(..., description="URL para consultar estado")


class SummarizationResult(BaseModel):
    """
    Resultado final de un resumen completado.

    Attributes:
        summary: Texto resumido generado por la IA.
        original_length: Longitud del texto original (en caracteres).
        summary_length: Longitud del resumen (en caracteres).
        language: Idioma del resumen generado.
    """

    summary: str = Field(..., description="Texto del resumen generado")
    original_length: int = Field(..., description="Longitud del texto original")
    summary_length: int = Field(..., description="Longitud del resumen")
    language: str = Field(..., description="Idioma del resumen")


# ==================== SERVICIO PRINCIPAL ====================


class SummarizationService:
    """
    Servicio para generar resúmenes de texto usando ApyHub AI API.

    Este servicio maneja la comunicación asíncrona con ApyHub,
    incluyendo el envío de jobs, polling de estado y obtención de resultados.

    Attributes:
        _api_token: Token de autenticación de ApyHub.
        _client: Cliente HTTP asíncrono para peticiones.
    """

    def __init__(self, api_token: str | None = None):
        """
        Inicializa el servicio de resúmenes.

        Args:
            api_token: Token de API de ApyHub. Si no se proporciona,
                      se usa el del archivo de configuración.
        """
        self._api_token = api_token or settings.APYHUB_TOKEN
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={
                "Content-Type": "application/json",
                "apy-token": self._api_token,
            },
        )

    async def __aenter__(self):
        """Soporte para context manager (async with)."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra el cliente HTTP al salir del context manager."""
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def submit_summarization_job(
        self,
        content: str,
        voice_tone: str = DEFAULT_VOICE_TONE,
        max_length: int = DEFAULT_MAX_LENGTH,
        language: str = DEFAULT_LANGUAGE,
    ) -> SummarizationJob:
        """
        Envía un texto para resumir y obtiene un job_id.

        Este método inicia el proceso de resumen. La API de ApyHub
        es asíncrona, por lo que devuelve un job_id que luego se
        debe consultar con get_summary_result().

        Args:
            content: Texto a resumir (máx. 10,000 caracteres recomendado).
            voice_tone: Tono del resumen (ej: "neutral", "funny", "professional").
            max_length: Longitud máxima del resumen en palabras.
            language: Idioma del resumen ("Spanish", "English", etc.).

        Returns:
            SummarizationJob con job_id y status_url.

        Raises:
            ApyHubAPIError: Si la API devuelve error.
            InvalidResponseError: Si la respuesta tiene formato inválido.

        Example:
            >>> service = SummarizationService()
            >>> job = await service.submit_summarization_job(
            ...     "Texto largo aquí...",
            ...     voice_tone="professional",
            ...     max_length=150
            ... )
            >>> print(job.job_id)
            '5de4887a-0dfd-49b6-8edb-9280e468c210'
        """
        payload = {
            "content": content,
            "voice_tone": voice_tone,
            "max_length": max_length,
            "language": language,
        }

        try:
            response = await self._client.post(SUMMARIZE_ENDPOINT, json=payload)
            response.raise_for_status()

            data = response.json()

            # Validar que la respuesta tenga los campos esperados
            if "job_id" not in data or "status_url" not in data:
                raise InvalidResponseError(f"Respuesta sin job_id o status_url: {data}")

            return SummarizationJob(job_id=data["job_id"], status_url=data["status_url"])

        except httpx.HTTPStatusError as error:
            raise ApyHubAPIError(
                f"Error HTTP {error.response.status_code}: {error.response.text}",
                status_code=error.response.status_code,
            ) from error
        except httpx.RequestError:  # ✅ Sin capturar variable innecesaria
            # Este error se reintenta automáticamente por el decorador @retry
            raise
        except Exception as error:
            raise SummarizationError(f"Error inesperado: {error}") from error

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def check_job_status(self, status_url: str) -> dict[str, Any]:
        """
        Consulta el estado de un job de resumen.

        IMPORTANTE: ApyHub devuelve una status_url con dominio incorrecto
        (apyhub.com en lugar de api.apyhub.com). Este método corrige la URL
        automáticamente.

        Args:
            status_url: URL proporcionada por ApyHub (será corregida automáticamente).

        Returns:
            Dict con el estado del job.

        Raises:
            ApyHubAPIError: Si la API devuelve error.
            InvalidResponseError: Si la respuesta tiene formato inválido.
        """
        # FIX: ApyHub devuelve URL con dominio incorrecto
        # Cambiar: https://apyhub.com/services/provider/sharpapi/...
        # Por:     https://api.apyhub.com/sharpapi/...
        corrected_url = status_url.replace(
            "https://apyhub.com/services/provider/sharpapi", "https://api.apyhub.com/sharpapi"
        )

        try:
            response = await self._client.get(corrected_url)
            response.raise_for_status()

            data = response.json()

            # Validar que la respuesta tenga al menos el campo 'status'
            if "status" not in data:
                raise InvalidResponseError(f"Respuesta sin campo 'status': {data}")

            return data

        except httpx.HTTPStatusError as error:
            raise ApyHubAPIError(
                f"Error HTTP {error.response.status_code}: {error.response.text}",
                status_code=error.response.status_code,
            ) from error
        except httpx.RequestError:
            # Este error se reintenta automáticamente por el decorador @retry
            raise
        except Exception as error:
            raise SummarizationError(f"Error inesperado: {error}") from error

    async def get_summary_result(
        self,
        content: str,
        voice_tone: str = DEFAULT_VOICE_TONE,
        max_length: int = DEFAULT_MAX_LENGTH,
        language: str = DEFAULT_LANGUAGE,
        timeout: int = JOB_TIMEOUT,
    ) -> SummarizationResult:
        """
        Genera un resumen de texto y espera el resultado.

        Este es el método principal para usar el servicio. Orquesta todo
        el proceso: envío del job, polling de estado y obtención del resultado.

        El método bloqueará hasta que el resumen esté listo o se agote el timeout.

        Args:
            content: Texto a resumir (máx. 10,000 caracteres recomendado).
            voice_tone: Tono del resumen (ej: "neutral", "funny", "professional").
            max_length: Longitud máxima del resumen en palabras.
            language: Idioma del resumen ("Spanish", "English", etc.).
            timeout: Tiempo máximo de espera en segundos (default: 300).

        Returns:
            SummarizationResult con el resumen generado y metadatos.

        Raises:
            SummarizationTimeoutError: Si se agota el timeout.
            ApyHubAPIError: Si la API devuelve error.
            InvalidResponseError: Si la respuesta tiene formato inválido.

        Example:
            >>> async with SummarizationService() as service:
            ...     result = await service.get_summary_result(
            ...         "Texto largo de una transcripción...",
            ...         voice_tone="professional",
            ...         max_length=200
            ...     )
            ...     print(result.summary)
            'Este es el resumen generado por la IA...'
        """
        # Paso 1: Enviar job de resumen
        job = await self.submit_summarization_job(
            content=content,
            voice_tone=voice_tone,
            max_length=max_length,
            language=language,
        )

        # Paso 2: Polling hasta obtener resultado
        start_time = asyncio.get_event_loop().time()
        attempts = 0

        while attempts < MAX_POLLING_ATTEMPTS:
            # Verificar timeout global
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise SummarizationTimeoutError(
                    f"Timeout de {timeout}s alcanzado esperando resumen (job_id: {job.job_id})"
                )

            # Consultar estado del job
            status_data = await self.check_job_status(job.status_url)
            job_status = status_data.get("status", "").lower()

            # Estado completado: extraer resultado
            if job_status == "completed":
                return self._parse_summary_result(status_data, content)

            # Estado fallido: lanzar error
            if job_status == "failed":
                error_msg = status_data.get("error", "Error desconocido")
                raise ApyHubAPIError(
                    f"El job de resumen falló: {error_msg}",
                    status_code=None,
                )

            # Estados pendientes: esperar y reintentar
            if job_status in ["pending", "processing"]:
                await asyncio.sleep(POLLING_INTERVAL)
                attempts += 1
                continue

            # Estado desconocido: advertir pero continuar
            # (por si ApyHub añade nuevos estados en el futuro)
            await asyncio.sleep(POLLING_INTERVAL)
            attempts += 1

        # Si llegamos aquí, agotamos todos los intentos
        raise SummarizationTimeoutError(
            f"Máximo de {MAX_POLLING_ATTEMPTS} intentos alcanzado (job_id: {job.job_id})"
        )

    def _parse_summary_result(
        self, status_data: dict[str, Any], original_content: str
    ) -> SummarizationResult:
        """
        Extrae el resultado del resumen desde la respuesta de ApyHub.

        Este método privado se encarga de parsear la estructura de datos
        que devuelve ApyHub cuando un job está completado.

        Args:
            status_data: Datos de la respuesta del job completado.
            original_content: Texto original para calcular longitud.

        Returns:
            SummarizationResult con datos validados.

        Raises:
            InvalidResponseError: Si falta información requerida.
        """
        # Validar que exista el campo 'result' o 'data' (puede variar según API)
        result_data = status_data.get("result") or status_data.get("data")

        if not result_data:
            raise InvalidResponseError(
                f"Respuesta completada sin campo 'result' o 'data': {status_data}"
            )

        # Extraer el texto del resumen
        # (Ajustar según estructura real de ApyHub)
        summary_text = result_data.get("summary") or result_data.get("content")

        if not summary_text:
            raise InvalidResponseError(f"Resultado sin texto de resumen: {result_data}")

        # Construir objeto de resultado
        return SummarizationResult(
            summary=summary_text,
            original_length=len(original_content),
            summary_length=len(summary_text),
            language=result_data.get("language", "Unknown"),
        )
