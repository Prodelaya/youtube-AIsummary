"""
Tests de integración para SummarizationService.

Estos tests realizan llamadas REALES a la API de ApyHub.
IMPORTANTE: Cada test consume 1 de tus 10 llamadas diarias.

Ejecutar con:
    pytest tests/integration/test_summarization_service.py -v

Skip si no hay token:
    pytest tests/integration/test_summarization_service.py -v -m "not integration"
"""

import asyncio

import pytest

from src.core.config import settings
from src.services.summarization_service import (
    ApyHubAPIError,
    InvalidResponseError,
    SummarizationService,
    SummarizationTimeoutError,
)

# Texto de prueba: corto pero con contenido suficiente para resumir
SAMPLE_TEXT = """
La inteligencia artificial está transformando el desarrollo de software de manera
profunda. Los modelos de lenguaje como GPT-4 y Claude permiten a los desarrolladores
escribir código más rápido mediante autocompletado inteligente y generación de código.
Las herramientas de IA también ayudan en la detección de bugs, revisión de código
y optimización de rendimiento. Sin embargo, es importante que los desarrolladores
mantengan un pensamiento crítico y no dependan completamente de estas herramientas.
La IA es un asistente poderoso, pero el conocimiento fundamental de programación
sigue siendo esencial para crear software robusto y mantenible.
"""


# ==================== FIXTURES ====================


@pytest.fixture
def skip_if_no_token():
    """
    Skip test si no hay token de ApyHub configurado.

    Útil para CI/CD donde no queremos consumir cuota en cada build.
    """
    if not settings.APYHUB_TOKEN or settings.APYHUB_TOKEN == "tu_token_de_apyhub_aqui":
        pytest.skip("ApyHub token no configurado, skip test de integración")


# ==================== TESTS ====================


@pytest.mark.asyncio
@pytest.mark.integration  # Marca para poder excluir con -m "not integration"
async def test_submit_summarization_job_success(skip_if_no_token):
    """
    Test: Enviar job de resumen devuelve job_id y status_url.

    Verifica que la API de ApyHub responde correctamente al enviar
    un texto para resumir.
    """
    async with SummarizationService() as service:
        # Enviar job
        job = await service.submit_summarization_job(
            content=SAMPLE_TEXT,
            voice_tone="neutral",
            max_length=100,
            language="Spanish",
        )

        # Verificar estructura de respuesta
        assert job.job_id is not None
        assert len(job.job_id) > 0
        assert job.status_url is not None
        assert "apyhub.com" in job.status_url

        print(f"\n✅ Job enviado exitosamente:")
        print(f"   Job ID: {job.job_id}")
        print(f"   Status URL: {job.status_url}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_summary_result_success(skip_if_no_token):
    """
    Test: Proceso completo de generación de resumen.

    Este es el test más importante: verifica que todo el flujo
    funciona correctamente (submit + polling + resultado).

    NOTA: Puede tardar 10-30 segundos en completar.
    """
    async with SummarizationService() as service:
        # Generar resumen completo
        result = await service.get_summary_result(
            content=SAMPLE_TEXT,
            voice_tone="professional",
            max_length=80,
            language="Spanish",
            timeout=60,  # 1 minuto debería ser suficiente
        )

        # Verificar resultado
        assert result.summary is not None
        assert len(result.summary) > 0
        assert result.summary_length > 0
        assert result.summary_length < len(SAMPLE_TEXT)  # Resumen más corto que original
        assert result.original_length == len(SAMPLE_TEXT)

        # Verificar que el resumen tiene sentido (contiene palabras clave)
        summary_lower = result.summary.lower()
        assert any(
            keyword in summary_lower
            for keyword in ["inteligencia", "artificial", "ia", "desarrollo", "software"]
        )

        print(f"\n✅ Resumen generado exitosamente:")
        print(f"   Longitud original: {result.original_length} chars")
        print(f"   Longitud resumen: {result.summary_length} chars")
        print(f"   Reducción: {100 - (result.summary_length * 100 / result.original_length):.1f}%")
        print(f"   Idioma: {result.language}")
        print(f"\n📄 Resumen:")
        print(f"   {result.summary}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_check_job_status_pending(skip_if_no_token):
    """
    Test: Consultar estado de un job recién creado.

    Verifica que podemos consultar el estado de un job.
    El job debería estar en estado 'pending' o 'processing'.
    """
    async with SummarizationService() as service:
        # Enviar job
        job = await service.submit_summarization_job(
            content=SAMPLE_TEXT[:200],  # Texto más corto
            max_length=50,
        )

        # Consultar estado inmediatamente (debería estar pending/processing)
        status = await service.check_job_status(job.status_url)

        assert "status" in status
        assert status["status"] in ["pending", "processing", "completed"]

        print(f"\n✅ Estado del job consultado:")
        print(f"   Job ID: {job.job_id}")
        print(f"   Estado: {status['status']}")


@pytest.mark.asyncio
async def test_submit_without_token_fails():
    """
    Test: Fallo al enviar sin token válido.

    Verifica que el servicio falla correctamente cuando
    el token no es válido.
    """
    # Usar token inválido
    service = SummarizationService(api_token="token_invalido_123")

    async with service:
        with pytest.raises(ApyHubAPIError) as exc_info:
            await service.submit_summarization_job(
                content="Texto de prueba",
                max_length=50,
            )

        # Verificar que el error contiene información útil
        assert exc_info.value.status_code in [401, 403]  # Unauthorized o Forbidden

        print(f"\n✅ Error detectado correctamente:")
        print(f"   Status code: {exc_info.value.status_code}")
        print(f"   Mensaje: {str(exc_info.value)}")


@pytest.mark.asyncio
async def test_empty_content_fails():
    """
    Test: Fallo al enviar contenido vacío.

    Verifica que el servicio maneja correctamente errores
    de validación de entrada.
    """
    async with SummarizationService() as service:
        with pytest.raises((ApyHubAPIError, InvalidResponseError)):
            await service.submit_summarization_job(
                content="",  # Contenido vacío
                max_length=50,
            )

        print("\n✅ Error de contenido vacío detectado correctamente")


# ==================== HELPER PARA PRUEBAS MANUALES ====================


async def manual_test():
    """
    Función helper para probar el servicio manualmente.

    Ejecutar con:
        python -c "import asyncio; from tests.integration.test_summarization_service import manual_test; asyncio.run(manual_test())"
    """
    print("🧪 Iniciando test manual del servicio de resúmenes...\n")

    async with SummarizationService() as service:
        print(f"📝 Texto original ({len(SAMPLE_TEXT)} caracteres):")
        print(f"{SAMPLE_TEXT}\n")

        print("⏳ Generando resumen (esto puede tardar 10-30 segundos)...\n")

        result = await service.get_summary_result(
            content=SAMPLE_TEXT,
            voice_tone="professional",
            max_length=100,
            language="Spanish",
        )

        print("✅ Resumen generado exitosamente!\n")
        print(f"📊 Estadísticas:")
        print(f"   - Original: {result.original_length} caracteres")
        print(f"   - Resumen: {result.summary_length} caracteres")
        print(
            f"   - Reducción: {100 - (result.summary_length * 100 / result.original_length):.1f}%"
        )
        print(f"   - Idioma: {result.language}\n")

        print(f"📄 Resumen:")
        print(f"{result.summary}\n")


if __name__ == "__main__":
    # Permitir ejecutar directamente el test manual
    asyncio.run(manual_test())
