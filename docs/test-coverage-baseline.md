# Test Coverage Baseline - Paso 24

**Fecha:** 2025-11-16
**Coverage actual:** 70.77%
**Objetivo:** >80%
**Gap:** -9.23%

---

## Resumen Ejecutivo

El proyecto actualmente tiene **377 tests pasando** pero el coverage es de **70.77%**, lo cual está **~9 puntos porcentuales por debajo** del objetivo del 80% configurado en `pyproject.toml`.

Además, hay **9 tests fallando** y **7 errores** que deben ser corregidos antes de añadir nuevos tests.

---

## Tests Fallando (16 total)

### 1. test_health_and_stats.py (2 failures)

**Errores:**
- `test_get_global_stats_with_data`: `assert 0 == 2` - Stats globales no cuentan videos correctamente
- `test_get_global_stats_source_breakdown`: `assert 0 >= 1` - Lista de sources vacía

**Causa raíz:** Servicio de stats no está calculando agregaciones correctamente, o bien hay un problema con los fixtures de datos.

**Impacto:** ALTO - Endpoint crítico de la API REST

---

### 2. test_sources_handler.py (1 failure)

**Error:**
- `test_toggle_subscribe_to_channel`: `Expected 'edit_message_reply_markup' to have been called once. Called 0 times`

**Causa raíz:** Handler del bot no está actualizando el teclado inline después del toggle de suscripción.

**Impacto:** MEDIO - UX del bot Telegram

---

### 3. test_downloader_service.py (2 failures)

**Errores:**
- `test_download_audio_success`: `DownloadError: ERROR: The downloaded file is empty`
- `test_audio_file_format_is_mp3`: `DownloadError: ERROR: The downloaded file is empty`

**Causa raíz:** yt-dlp descargando archivo vacío en tests de integración. Posiblemente el video de prueba fue eliminado o restringido.

**Impacto:** CRÍTICO - Proceso core de descarga

---

### 4. test_summarization_service.py (3 failures)

**Errores:**
- `test_generate_summary_with_database`: `TypeError: 'duration' is an invalid keyword argument for Video`
- `test_generate_summary_transcription_not_found`: `sqlalchemy.exc.ProgrammingError: relation "transcriptions" does not exist`
- `test_generate_summary_duplicate_error`: `TypeError: 'duration' is an invalid keyword argument for Video`

**Causa raíz:**
1. Modelo `Video` espera `duration_seconds` no `duration`
2. Tabla `transcriptions` no existe en BD de test (migración faltante o schema inconsistente)

**Impacto:** CRÍTICO - Pipeline de resúmenes

---

### 5. test_transcription_service.py (1 error)

**Error:**
- `test_transcribe_audio_success`: `UnboundLocalError: cannot access local variable 'audio_path' where it is not associated with a value`

**Causa raíz:** Variable `audio_path` no inicializada en algún path del código.

**Impacto:** ALTO - Proceso de transcripción

---

### 6. test_distribute_summaries.py (7 errors)

**Errores:** Todos los tests fallan con errores de imports o configuración

**Causa raíz:** Test requiere configuración específica de mocks o fixtures. Posible problema con imports de módulos.

**Impacto:** CRÍTICO - Distribución a usuarios Telegram

---

## Módulos con Coverage Crítico (<50%)

| Módulo | Coverage | Líneas sin cubrir | Prioridad |
|--------|----------|------------------|-----------|
| `src/services/youtube_scraper_service.py` | **0%** | 91 líneas | 🔴 CRÍTICO |
| `src/tasks/scraping.py` | **0%** | 84 líneas | 🔴 CRÍTICO |
| `src/tasks/video_processing.py` | **28%** | 57 líneas | 🔴 ALTA |
| `src/tasks/distribute_summaries.py` | **32%** | 67 líneas | 🔴 ALTA |
| `src/services/telegram_service.py` | **42%** | 142 líneas | 🟡 MEDIA |

---

## Módulos con Coverage Bajo (50-80%)

| Módulo | Coverage | Líneas sin cubrir | Notas |
|--------|----------|------------------|-------|
| `src/services/stats_service.py` | **54%** | 62 líneas | Tests failing detectados |
| `src/services/cache_service.py` | **66%** | 45 líneas | Ampliar tests de invalidación |
| `src/services/downloader_service.py` | **72%** | 48 líneas | Tests failing detectados |
| `src/services/transcription_service.py` | **86%** | 13 líneas | Casi completo (solo edge cases) |

---

## Módulos con Coverage Excelente (>90%)

| Módulo | Coverage | Notas |
|--------|----------|-------|
| `src/services/video_processing_service.py` | **94%** | Excelente cobertura |
| `src/bot/formatters.py` | **100%** | Cobertura completa |
| `src/bot/handlers/start.py` | **100%** | Cobertura completa |
| `src/repositories/base_repository.py` | **96%** | Muy bueno |
| `src/core/metrics.py` | **100%** | Cobertura completa |

---

## Plan de Acción

### Fase 1: Estabilización (PRIORIDAD MÁXIMA)

1. **Arreglar test_health_and_stats.py**
   - Revisar servicio de stats
   - Verificar fixtures de datos
   - Confirmar que agregaciones SQL funcionan

2. **Arreglar test_sources_handler.py**
   - Añadir llamada a `edit_message_reply_markup` en handler
   - Actualizar teclado inline después del toggle

3. **Arreglar test_downloader_service.py**
   - Usar video de prueba válido y estable
   - Considerar mockear yt-dlp en tests unitarios

4. **Arreglar test_summarization_service.py**
   - Cambiar `duration` → `duration_seconds` en fixtures
   - Verificar schema de BD tiene tabla `transcriptions`
   - Ejecutar migraciones de Alembic si faltan

5. **Arreglar test_transcription_service.py**
   - Inicializar `audio_path` correctamente
   - Revisar flujo de ejecución

6. **Arreglar test_distribute_summaries.py**
   - Revisar imports y fixtures
   - Verificar configuración de mocks

**Meta:** 0 failures, 100% de tests pasando

---

### Fase 2: Coverage de Gaps Críticos (0% coverage)

**Módulos a testear:**

1. `youtube_scraper_service.py` (0% → >80%)
   - ~10 tests unitarios con mocks de feeds YouTube
   - Tests de parseo de metadata
   - Tests de error handling

2. `scraping.py` (tasks) (0% → >70%)
   - ~6 tests de tarea Celery
   - Mock de scraper service
   - Tests de retry logic

3. `video_processing.py` (tasks) (28% → >75%)
   - ~5 tests adicionales
   - Casos de error y rollback
   - Tests de state transitions

4. `distribute_summaries.py` (32% → >75%)
   - ~7 tests adicionales (ya hay algunos que fallan)
   - Casos de Telegram API errors
   - Tests de idempotencia

**Impacto esperado:** +15-18% de coverage global

---

### Fase 3: Ampliar Coverage de Servicios Core

**Módulos a ampliar:**

1. `telegram_service.py` (42% → >80%)
   - ~10 tests de envío de mensajes
   - Error handling (Forbidden, TimedOut, RetryAfter)
   - Tests de formateo de mensajes

2. `stats_service.py` (54% → >85%)
   - ~6 tests de cálculo de estadísticas
   - Tests de cache integration
   - Tests de agregaciones complejas

3. `cache_service.py` (66% → >85%)
   - ~5 tests de invalidación
   - Tests de TTL y expiration
   - Tests de namespaces

4. `downloader_service.py` (72% → >85%)
   - ~4 tests de edge cases
   - Tests de error handling
   - Tests de cleanup de archivos

**Impacto esperado:** +5-7% de coverage global

---

### Fase 4: Validación Final

1. Ejecutar suite completa con coverage
2. Verificar >80% alcanzado
3. Generar reporte HTML
4. Documentar estrategia de testing

---

## Estimación de Tests Necesarios

| Fase | Tests a añadir/arreglar | Coverage esperado | Tiempo estimado |
|------|------------------------|-------------------|-----------------|
| Fase 1: Estabilización | 16 tests (arreglar) | 70.77% (mantener) | 2-3h |
| Fase 2: Gaps críticos | ~28 tests nuevos | +16% → **86%** | 3-4h |
| Fase 3: Servicios core | ~25 tests nuevos | +6% → **92%** | 2-3h |
| Fase 4: Validación | 0 tests (docs) | 92% (confirmar) | 1h |
| **TOTAL** | **~53 tests nuevos** | **>90% coverage** | **8-11h** |

---

## Configuración Actual de Coverage

Desde `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=80",  # ← Objetivo: >80%
]
```

---

## Próximos Pasos

1. ✅ Generar este baseline document
2. ⏳ Arreglar 16 tests fallando (Fase 1)
3. ⏳ Implementar tests para módulos con 0% coverage (Fase 2)
4. ⏳ Ampliar coverage de servicios core (Fase 3)
5. ⏳ Validación final y documentación (Fase 4)

---

**Documento generado:** 2025-11-16
**Autor:** Claude Code (Paso 24 del Roadmap)
