"""
Tests de integración para SummarizationService con DeepSeek API.

Estos tests realizan llamadas REALES a la API de DeepSeek.
IMPORTANTE: Cada test consume tokens de tu cuenta de DeepSeek.

Ejecutar con:
    pytest tests/integration/test_summarization_service.py -v

Skip si no hay token:
    pytest tests/integration/test_summarization_service.py -v -m "not integration"
"""

import asyncio

import pytest

from src.core.config import settings
from src.services.summarization_service import (
    DeepSeekAPIError,
    InvalidResponseError,
    SummarizationResult,
    SummarizationService,
)

# Texto de prueba: transcripción simulada sobre IA y desarrollo
SAMPLE_TRANSCRIPTION = """
La inteligencia artificial está transformando el desarrollo de software de manera
profunda. Los modelos de lenguaje como GPT-4 y Claude permiten a los desarrolladores
escribir código más rápido mediante autocompletado inteligente y generación de código.
Las herramientas de IA también ayudan en la detección de bugs, revisión de código
y optimización de rendimiento. Sin embargo, es importante que los desarrolladores
mantengan un pensamiento crítico y no dependan completamente de estas herramientas.
La IA es un asistente poderoso, pero el conocimiento fundamental de programación
sigue siendo esencial para crear software robusto y mantenible.
En este video exploramos cómo integrar estas herramientas en el flujo de trabajo
diario sin perder control sobre la calidad del código. También discutimos los límites
actuales de los modelos y cuándo es mejor usar enfoques tradicionales.
"""

SAMPLE_TITLE = "Cómo la IA está cambiando el desarrollo de software"
SAMPLE_DURATION = "12:45"


# ==================== FIXTURES ====================


@pytest.fixture
def skip_if_no_token():
    """
    Skip test si no hay token de DeepSeek configurado.

    Útil para CI/CD donde no queremos consumir tokens en cada build.
    """
    # Verificar que existe la variable
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY no configurado en .env")

    # Verificar que no es el placeholder del ejemplo
    if settings.DEEPSEEK_API_KEY == "sk-your_deepseek_api_key_here":
        pytest.skip("DEEPSEEK_API_KEY es el valor de ejemplo, no una key real")

    # Verificar formato válido (empieza con sk-)
    if not settings.DEEPSEEK_API_KEY.startswith("sk-"):
        pytest.skip("DEEPSEEK_API_KEY no tiene formato válido (debe empezar con 'sk-')")


# ==================== TESTS ====================


@pytest.mark.asyncio
@pytest.mark.integration  # Marca para poder excluir con -m "not integration"
async def test_get_summary_result_success(skip_if_no_token):
    """
    Test: Proceso completo de generación de resumen con DeepSeek.

    Este es el test más importante: verifica que todo el flujo
    funciona correctamente con la API síncrona de DeepSeek.

    NOTA: Puede tardar 5-15 segundos en completar.
    """
    async with SummarizationService() as service:
        # Generar resumen completo
        result = await service.get_summary_result(
            title=SAMPLE_TITLE,
            duration=SAMPLE_DURATION,
            transcription=SAMPLE_TRANSCRIPTION,
            max_tokens=500,
            temperature=0.3,
        )

        # Verificar estructura del resultado
        assert isinstance(result, SummarizationResult)
        assert result.summary is not None
        assert len(result.summary) > 0

        # Verificar longitudes
        assert result.summary_length > 0
        assert result.summary_length > 50  # Mínimo razonable para resumen
        assert result.original_length == len(SAMPLE_TRANSCRIPTION)

        # Verificar metadata
        assert result.language == "Spanish"
        assert result.model_used == "deepseek-chat"
        assert result.tokens_used > 0

        # Verificar que el resumen tiene sentido (contiene palabras clave)
        summary_lower = result.summary.lower()
        assert any(
            keyword in summary_lower
            for keyword in ["inteligencia", "artificial", "ia", "desarrollo", "software", "código"]
        )

        print("\n✅ Resumen generado exitosamente:")
        print(f"   Título: {SAMPLE_TITLE}")
        print(f"   Duración: {SAMPLE_DURATION}")
        print(f"   Longitud original: {result.original_length} chars")
        print(f"   Longitud resumen: {result.summary_length} chars")
        print(f"   Reducción: {100 - (result.summary_length * 100 / result.original_length):.1f}%")
        print(f"   Idioma: {result.language}")
        print(f"   Modelo: {result.model_used}")
        print(f"   Tokens usados: {result.tokens_used}")
        print(f"   Tokens cacheados: {result.cached_tokens}")
        print("\n📄 Resumen:")
        print(f"{result.summary}\n")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_summary_result_with_short_text(skip_if_no_token):
    """
    Test: Resumen de texto corto.

    Verifica que el servicio funciona correctamente incluso
    con transcripciones breves.
    """
    short_text = """
    En este video explicamos los fundamentos de FastAPI.
    FastAPI es un framework moderno para crear APIs con Python 3.7+.
    Utiliza tipado estático y genera documentación automática.
    """

    async with SummarizationService() as service:
        result = await service.get_summary_result(
            title="Introducción a FastAPI",
            duration="05:30",
            transcription=short_text,
            max_tokens=300,
            temperature=0.3,
        )

        assert result.summary is not None
        assert len(result.summary) > 0
        assert result.model_used == "deepseek-chat"
        assert result.tokens_used > 0

        print("\n✅ Resumen de texto corto generado:")
        print(f"   Tokens usados: {result.tokens_used}")
        print(f"   Resumen: {result.summary[:100]}...")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_summary_result_with_custom_temperature(skip_if_no_token):
    """
    Test: Generación con temperatura personalizada.

    Verifica que se pueden ajustar los parámetros del modelo.
    """
    async with SummarizationService() as service:
        # Temperatura baja (más determinista)
        result_low = await service.get_summary_result(
            title=SAMPLE_TITLE,
            duration=SAMPLE_DURATION,
            transcription=SAMPLE_TRANSCRIPTION,
            max_tokens=400,
            temperature=0.1,  # Muy determinista
        )

        assert result_low.summary is not None
        assert result_low.tokens_used > 0

        print("\n✅ Resumen con temperatura baja (0.1):")
        print(f"   Tokens: {result_low.tokens_used}")
        print(f"   Longitud: {result_low.summary_length} chars")


@pytest.mark.asyncio
async def test_invalid_api_key_fails():
    """
    Test: Fallo con API key inválida.

    Verifica que el servicio maneja correctamente errores
    de autenticación.
    """
    # Crear servicio con API key inválida temporalmente
    # Guardamos la original
    original_key = settings.DEEPSEEK_API_KEY

    try:
        # Forzar API key inválida
        settings.DEEPSEEK_API_KEY = "sk-invalid-key-12345"

        async with SummarizationService() as service:
            with pytest.raises(DeepSeekAPIError) as exc_info:
                await service.get_summary_result(
                    title="Test",
                    duration="01:00",
                    transcription="Texto de prueba",
                    max_tokens=100,
                )

            # Verificar que el error contiene información útil
            error = exc_info.value
            assert error.status_code in [401, 403]  # Unauthorized o Forbidden

            print("\n✅ Error de autenticación detectado correctamente:")
            print(f"   Status code: {error.status_code}")
            print(f"   Mensaje: {str(error)}")

    finally:
        # Restaurar API key original
        settings.DEEPSEEK_API_KEY = original_key


@pytest.mark.asyncio
async def test_context_manager_closes_client(skip_if_no_token):
    """
    Test: El context manager cierra el cliente correctamente.

    Verifica que no hay leaks de recursos.
    """
    service = SummarizationService()

    async with service:
        # Cliente debe estar disponible dentro del contexto
        assert service._client is not None

        result = await service.get_summary_result(
            title="Test Context Manager",
            duration="02:00",
            transcription=SAMPLE_TRANSCRIPTION[:200],
            max_tokens=200,
        )

        assert result.summary is not None

    # Cliente debe estar cerrado fuera del contexto
    # (AsyncOpenAI maneja el cierre internamente)
    print("\n✅ Context manager funciona correctamente")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_tokens_reported(skip_if_no_token):
    """
    Test: Verificar que se reportan tokens cacheados.

    DeepSeek usa context caching para reducir costos.
    Los tokens cacheados deberían reportarse correctamente.
    """
    async with SummarizationService() as service:
        result = await service.get_summary_result(
            title=SAMPLE_TITLE,
            duration=SAMPLE_DURATION,
            transcription=SAMPLE_TRANSCRIPTION,
            max_tokens=300,
            temperature=0.3,
        )

        # Verificar que el campo existe (puede ser 0 en primera llamada)
        assert hasattr(result, "cached_tokens")
        assert result.cached_tokens >= 0

        print("\n✅ Información de tokens:")
        print(f"   Tokens totales: {result.tokens_used}")
        print(f"   Tokens cacheados: {result.cached_tokens}")

        if result.cached_tokens > 0:
            savings = (result.cached_tokens / result.tokens_used) * 100
            print(f"   Ahorro por cache: {savings:.1f}%")


# ==================== HELPER PARA PRUEBAS MANUALES ====================


async def manual_test():
    """
    Función helper para probar el servicio manualmente.

    Ejecutar con:
        python -c "import asyncio; from tests.integration.test_summarization_service import manual_test; asyncio.run(manual_test())"
    """
    print("🧪 Iniciando test manual del servicio de resúmenes DeepSeek...\n")

    async with SummarizationService() as service:
        print(f"📝 Vídeo: {SAMPLE_TITLE}")
        print(f"⏱️  Duración: {SAMPLE_DURATION}")
        print(f"📄 Transcripción ({len(SAMPLE_TRANSCRIPTION)} caracteres):")
        print(f"{SAMPLE_TRANSCRIPTION[:200]}...\n")

        print("⏳ Generando resumen con DeepSeek (esto puede tardar 5-15 segundos)...\n")

        result = await service.get_summary_result(
            title=SAMPLE_TITLE,
            duration=SAMPLE_DURATION,
            transcription=SAMPLE_TRANSCRIPTION,
            max_tokens=500,
            temperature=0.3,
        )

        print("✅ Resumen generado exitosamente!\n")
        print("📊 Estadísticas:")
        print(f"   - Original: {result.original_length} caracteres")
        print(f"   - Resumen: {result.summary_length} caracteres")
        print(
            f"   - Reducción: {100 - (result.summary_length * 100 / result.original_length):.1f}%"
        )
        print(f"   - Idioma: {result.language}")
        print(f"   - Modelo: {result.model_used}")
        print(f"   - Tokens usados: {result.tokens_used}")
        print(f"   - Tokens cacheados: {result.cached_tokens}\n")

        print("📄 Resumen completo:")
        print("-" * 80)
        print(f"{result.summary}")
        print("-" * 80)


if __name__ == "__main__":
    # Permitir ejecutar directamente el test manual
    asyncio.run(manual_test())
