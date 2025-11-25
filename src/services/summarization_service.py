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

import time
from uuid import UUID

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.config import settings
from src.models import Summary, Transcription, Video
from src.repositories.exceptions import AlreadyExistsError, NotFoundError
from src.repositories.summary_repository import SummaryRepository
from src.repositories.transcription_repository import TranscriptionRepository
from src.services.input_sanitizer import InputSanitizer
from src.services.output_validator import OutputValidator
from src.services.prompts import format_user_prompt, load_prompt

# ==================== CONSTANTES ====================
# Timeouts de red (en segundos)
REQUEST_TIMEOUT = 60  # Timeout para la llamada a la API

# Parámetros adicionales del modelo
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

        # Inicializar sanitizer y validator
        self._sanitizer = InputSanitizer()
        self._validator = OutputValidator()

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
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> SummarizationResult:
        """
        Genera un resumen de una transcripción de vídeo.

        Este es el método principal del servicio. Orquesta la generación del prompt,
        llamada a la API y parseo del resultado.

        Args:
            title: Título del vídeo.
            duration: Duración formateada (ej: "15:30").
            transcription: Texto de la transcripción completa.
            max_tokens: Máximo de tokens a generar (default: de settings.DEEPSEEK_MAX_TOKENS).
            temperature: Temperatura del modelo (0-2, default: de settings.DEEPSEEK_TEMPERATURE).

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
        # Usar valores de settings si no se proporcionan
        max_tokens = max_tokens or settings.DEEPSEEK_MAX_TOKENS
        temperature = temperature if temperature is not None else settings.DEEPSEEK_TEMPERATURE

        # SEGURIDAD: Sanitizar inputs antes de enviar al LLM
        sanitized_title = self._sanitizer.sanitize_title(title)
        sanitized_transcription = self._sanitizer.sanitize_transcription(transcription)

        # Generar user prompt con datos sanitizados
        user_prompt = format_user_prompt(
            title=sanitized_title,
            duration=duration,
            transcription=sanitized_transcription,
        )

        try:
            # Llamada a DeepSeek API con JSON mode forzado
            response = await self._client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=DEFAULT_TOP_P,
                response_format={"type": "json_object"},  # SEGURIDAD: Forzar JSON estructurado
            )

            # Extraer resultado
            if not response.choices or len(response.choices) == 0:
                raise InvalidResponseError("La API no devolvió ningún choice")

            content = response.choices[0].message.content

            if not content:
                raise InvalidResponseError("El resumen generado está vacío")

            # Parsear JSON response
            import json

            try:
                parsed_response = json.loads(content)
                summary_text = parsed_response.get("summary", "")

                if not summary_text:
                    raise InvalidResponseError("El campo 'summary' está vacío en la respuesta JSON")

            except json.JSONDecodeError as e:
                raise InvalidResponseError(f"La API no devolvió JSON válido: {e}")

            # SEGURIDAD: Detectar prompt leak en el output
            if self._validator.detect_prompt_leak(summary_text):
                raise InvalidResponseError("LLM output contains prompt leak")

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
                model_used=settings.DEEPSEEK_MODEL,
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

    async def generate_summary(self, session: Session, transcription_id: UUID) -> Summary:
        """
        Genera un resumen completo a partir de una transcripción y lo persiste en BD.

        Este método orquesta todo el proceso:
        1. Valida que la transcripción existe
        2. Verifica que no existe resumen previo (evita duplicados)
        3. Obtiene metadata del vídeo (título, duración)
        4. Llama a DeepSeek API para generar el resumen
        5. Extrae keywords automáticamente
        6. Categoriza el contenido
        7. Calcula métricas y guarda en BD

        Args:
            session: Sesión de SQLAlchemy para acceso a BD.
            transcription_id: UUID de la transcripción a resumir.

        Returns:
            Summary: Objeto Summary persistido en BD con todos los campos poblados.

        Raises:
            NotFoundError: Si la transcripción no existe.
            AlreadyExistsError: Si ya existe un resumen para esa transcripción.
            DeepSeekAPIError: Si falla la llamada a DeepSeek API.
            SummarizationError: Otros errores inesperados.

        Example:
            >>> async with SummarizationService() as service:
            ...     summary = await service.generate_summary(session, transcription_id)
            ...     print(f"Resumen generado: {summary.summary_text[:100]}...")
        """
        # Inicializar repositorios
        transcription_repo = TranscriptionRepository(session)
        summary_repo = SummaryRepository(session)

        # 1. Validar que transcripción existe
        transcription = transcription_repo.get_by_id(transcription_id)
        if not transcription:
            raise NotFoundError("Transcription", transcription_id)

        # 2. Verificar que no existe resumen previo (evitar duplicados)
        existing_summary = summary_repo.get_by_transcription_id(transcription_id)
        if existing_summary:
            raise AlreadyExistsError("Summary", "transcription_id", transcription_id)

        # 3. Obtener metadata del vídeo (eager loading via relationship)
        video: Video = transcription.video  # type: ignore
        if not video:
            raise SummarizationError(
                f"Transcription {transcription_id} no tiene video asociado (integridad de BD violada)"
            )

        # Formatear duración para el prompt (de segundos a MM:SS)
        duration_str = f"{video.duration // 60}:{video.duration % 60:02d}"

        # 4. Llamar a DeepSeek API
        start_time = time.time()

        result = await self.get_summary_result(
            title=video.title,
            duration=duration_str,
            transcription=transcription.transcription,
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # 5. Extraer keywords automáticamente
        keywords = extract_keywords(result.summary)

        # 6. Categorizar contenido
        category = categorize_summary(result.summary, keywords)

        # 7. Crear objeto Summary y persistir
        summary = Summary(
            transcription_id=transcription_id,
            summary_text=result.summary,
            keywords=keywords,
            category=category,
            model_used=result.model_used,
            tokens_used=result.tokens_used,
            input_tokens=result.tokens_used - result.cached_tokens,  # Aproximación
            output_tokens=result.cached_tokens,  # Aproximación
            processing_time_ms=processing_time_ms,
            extra_metadata={
                "original_length": result.original_length,
                "summary_length": result.summary_length,
                "language": result.language,
                "cached_tokens": result.cached_tokens,
            },
        )

        # Guardar en BD
        created_summary = summary_repo.create(summary)
        session.commit()

        return created_summary


# ==================== FUNCIONES HELPER ====================


def extract_keywords(summary_text: str, max_keywords: int = 8) -> list[str]:
    """
    Extrae keywords del texto del resumen.

    Usa heurísticas simples para identificar términos técnicos relevantes:
    - Palabras capitalizadas (nombres propios, frameworks)
    - Palabras con guiones o caracteres especiales (TypeScript, FastAPI)
    - Términos técnicos comunes

    Args:
        summary_text: Texto del resumen generado.
        max_keywords: Número máximo de keywords a extraer (default: 8).

    Returns:
        Lista de keywords únicas extraídas del texto.

    Example:
        >>> summary = "Este vídeo explica FastAPI y Python para crear APIs REST..."
        >>> extract_keywords(summary)
        ['FastAPI', 'Python', 'APIs REST']
    """
    import re

    # Patrones para identificar keywords
    # Palabras capitalizadas (ej: Python, FastAPI, Docker)
    capitalized = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b", summary_text)

    # Palabras con guiones o caracteres especiales (ej: TypeScript, yt-dlp)
    special = re.findall(r"\b\w+[-_]\w+\b", summary_text)

    # Acronyms y siglas (ej: API, REST, LLM)
    acronyms = re.findall(r"\b[A-Z]{2,}\b", summary_text)

    # Combinar todos los keywords encontrados
    all_keywords = capitalized + special + acronyms

    # Eliminar duplicados preservando orden
    seen = set()
    unique_keywords = []
    for kw in all_keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw)

    # Limitar al máximo especificado
    return unique_keywords[:max_keywords]


def categorize_summary(summary_text: str, keywords: list[str]) -> str:
    """
    Categoriza un resumen basándose en su contenido.

    Categorías disponibles:
    - "framework": Frameworks web/backend (FastAPI, Django, React, Vue)
    - "language": Lenguajes de programación (Python, JavaScript, Rust)
    - "tool": Herramientas de desarrollo (Docker, Git, VS Code)
    - "concept": Conceptos generales de IA/ML/desarrollo

    Args:
        summary_text: Texto del resumen.
        keywords: Lista de keywords extraídas.

    Returns:
        Categoría asignada (string).

    Example:
        >>> categorize_summary("FastAPI es un framework...", ["FastAPI", "Python"])
        'framework'
    """
    text_lower = summary_text.lower()
    keywords_lower = [k.lower() for k in keywords]

    # Diccionario de patrones para cada categoría
    patterns = {
        "framework": [
            "fastapi",
            "django",
            "flask",
            "react",
            "vue",
            "angular",
            "nextjs",
            "express",
            "spring",
            "laravel",
        ],
        "language": [
            "python",
            "javascript",
            "typescript",
            "rust",
            "go",
            "java",
            "c++",
            "kotlin",
            "swift",
        ],
        "tool": [
            "docker",
            "kubernetes",
            "git",
            "github",
            "vscode",
            "vim",
            "redis",
            "postgresql",
            "nginx",
        ],
    }

    # Contar coincidencias por categoría
    scores = {category: 0 for category in patterns}

    for category, terms in patterns.items():
        for term in terms:
            # Buscar en texto y keywords
            if term in text_lower:
                scores[category] += 2  # Mayor peso en texto
            if term in keywords_lower:
                scores[category] += 3  # Mayor peso en keywords

    # Obtener categoría con mayor score
    max_score = max(scores.values())

    if max_score > 0:
        return max(scores, key=scores.get)  # type: ignore

    # Default: concept
    return "concept"
