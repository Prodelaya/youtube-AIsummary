# Estrategia de Testing - Paso 24

**Fecha:** 2025-11-16
**Autor:** Claude Code
**Coverage objetivo:** >80%
**Coverage actual:** 70.77%

---

## 📋 Resumen Ejecutivo

Este documento define la estrategia de testing del proyecto youtube-AIsummary para alcanzar y mantener un coverage >80% con una suite de tests robusta y mantenible.

---

## 🎯 Objetivos

### Objetivos Primarios
1. **Coverage >80%**: Alcanzar y mantener cobertura mínima del 80%
2. **Suite verde**: 0 failures, todos los tests pasando
3. **Tests rápidos**: Suite completa ejecuta en <3 minutos
4. **Confianza alta**: Tests validan comportamiento crítico del sistema

### Objetivos Secundarios
1. **Documentación completa**: Guías de testing para futuros desarrolladores
2. **CI/CD ready**: Tests automáticos en cada push (Paso 25)
3. **Mantenibilidad**: Tests fáciles de entender y modificar
4. **Escalabilidad**: Estructura que soporta crecimiento del proyecto

---

## 🏗️ Pirámide de Testing

Seguimos la pirámide de testing clásica:

```
        /\
       /E2E\         ← 5-10% tests, flujos completos (FUTURO)
      /──────\
     /  INTEG \      ← 20-30% tests, integración servicios
    /──────────\
   /    UNIT    \    ← 60-75% tests, lógica de negocio
  /──────────────\
```

### Distribución Actual (Estimada)

| Tipo | Tests Actuales | Tests Objetivo | % Total |
|------|---------------|---------------|---------|
| **Unit** | ~250 | ~300 | ~65% |
| **Integration** | ~120 | ~150 | ~30% |
| **E2E** | 0 | 10-15 | ~5% |
| **TOTAL** | ~370 | ~460-465 | 100% |

---

## 📊 Estado Actual (Baseline)

### Coverage por Módulo

#### ✅ Excelente (>90%)
- `src/core/metrics.py`: 100%
- `src/bot/formatters.py`: 100%
- `src/bot/handlers/start.py`: 100%
- `src/services/video_processing_service.py`: 94%
- `src/repositories/base_repository.py`: 96%

#### 🟡 Bueno (70-90%)
- `src/services/transcription_service.py`: 86%
- `src/core/logging_config.py`: 87%
- `src/models/video.py`: 88%

#### 🟠 Mejorable (50-70%)
- `src/services/downloader_service.py`: 72%
- `src/services/cache_service.py`: 66%
- `src/services/stats_service.py`: 54%

#### 🔴 Crítico (<50%)
- `src/services/telegram_service.py`: 42%
- `src/tasks/distribute_summaries.py`: 32%
- `src/tasks/video_processing.py`: 28%
- `src/services/youtube_scraper_service.py`: 0%
- `src/tasks/scraping.py`: 0%

---

## 🎯 Plan de Acción (4 Fases)

### FASE 1: Estabilización (1.5h) - EN PROGRESO

**Objetivo:** Suite verde (0 failures)

**Tests a arreglar:**
- ✅ test_health_and_stats.py (2 tests) - COMPLETADO
- ✅ test_sources_handler.py (1 test) - COMPLETADO
- ⏳ test_downloader_service.py (2 tests) - En progreso
- ⏳ test_summarization_service.py (3 tests) - Pendiente
- ⏳ test_distribute_summaries.py (7 tests) - Pendiente

**Criterio de éxito:** `pytest` sin failures

---

### FASE 2: Tests para Módulos Críticos (0% coverage) (3-4h)

**Objetivo:** Cubrir módulos con 0% coverage hasta >70%

#### 2.1 youtube_scraper_service.py (0% → >80%)
**Tests a implementar (~10 tests):**

```python
# tests/unit/services/test_youtube_scraper_service.py

def test_parse_youtube_feed_success():
    """Parsea feed RSS de YouTube correctamente."""
    pass

def test_parse_youtube_feed_empty():
    """Maneja feed vacío sin errores."""
    pass

def test_extract_video_metadata_from_entry():
    """Extrae metadata correcta de entry RSS."""
    pass

def test_filter_videos_by_date():
    """Filtra videos por fecha de publicación."""
    pass

def test_handle_invalid_feed_format():
    """Maneja feeds malformados."""
    pass

def test_scrape_channel_success():
    """Scrape completo de canal exitoso."""
    pass

def test_scrape_channel_network_error():
    """Maneja errores de red."""
    pass

def test_scrape_channel_timeout():
    """Maneja timeouts."""
    pass

def test_parse_duration_from_metadata():
    """Parsea duración correctamente."""
    pass

def test_deduplicate_videos():
    """Elimina videos duplicados."""
    pass
```

**Técnicas:**
- Mocks de requests HTTP para feeds RSS
- Fixtures con XMLs de ejemplo
- Tests de parseo de metadata
- Tests de error handling

---

#### 2.2 scraping.py (tasks) (0% → >70%)
**Tests a implementar (~6 tests):**

```python
# tests/tasks/test_scraping.py

@patch("src.tasks.scraping.SessionLocal")
@patch("src.tasks.scraping.YouTubeScraperService")
def test_scrape_active_sources_success():
    """Scrape de todas las fuentes activas exitoso."""
    pass

def test_scrape_source_no_new_videos():
    """Fuente sin videos nuevos."""
    pass

def test_scrape_source_creates_videos_in_db():
    """Videos descubiertos se guardan en BD."""
    pass

def test_scrape_source_handles_duplicates():
    """Videos duplicados no se crean."""
    pass

def test_scrape_task_celery_retry_on_error():
    """Celery reintenta en caso de error."""
    pass

def test_scrape_multiple_sources_parallel():
    """Múltiples fuentes se procesan correctamente."""
    pass
```

**Técnicas:**
- Mocks de Celery task
- Mocks de SessionLocal
- Fixtures de Source y Video
- Tests de idempotencia

---

#### 2.3 video_processing.py (tasks) (28% → >75%)
**Tests adicionales (~5 tests):**

```python
# tests/tasks/test_video_processing.py

def test_process_video_task_complete_flow():
    """Pipeline completo: download → transcribe → summarize."""
    pass

def test_process_video_download_fails():
    """Maneja fallo en download."""
    pass

def test_process_video_transcription_fails():
    """Maneja fallo en transcripción."""
    pass

def test_process_video_summary_fails():
    """Maneja fallo en resumen."""
    pass

def test_process_video_rollback_on_error():
    """Rollback de BD en caso de error."""
    pass
```

---

#### 2.4 distribute_summaries.py (32% → >75%)
**Tests adicionales (~7 tests):**

Ya existe suite básica, completar con:
- Tests de rate limiting de Telegram
- Tests de usuarios bloqueados
- Tests de idempotencia (no reenviar)
- Tests de formato de mensajes

---

### FASE 3: Ampliar Coverage de Servicios Core (2-3h)

**Objetivo:** Servicios críticos >85% coverage

#### 3.1 telegram_service.py (42% → >80%)
**Tests a implementar (~10 tests):**

```python
# tests/services/test_telegram_service.py

def test_send_message_success():
    """Envío exitoso de mensaje."""
    pass

def test_send_message_user_blocked_bot():
    """Maneja error Forbidden (usuario bloqueó bot)."""
    pass

def test_send_message_rate_limit():
    """Maneja error RetryAfter."""
    pass

def test_send_message_timeout():
    """Maneja timeout de Telegram."""
    pass

def test_send_message_network_error():
    """Maneja error de red."""
    pass

def test_format_summary_message():
    """Formatea mensaje de resumen correctamente."""
    pass

def test_send_message_with_markdown():
    """Markdown parseado correctamente."""
    pass

def test_send_message_long_text_truncated():
    """Textos largos se truncan correctamente."""
    pass

def test_send_message_with_inline_keyboard():
    """Envía teclado inline correctamente."""
    pass

def test_batch_send_messages():
    """Envío en batch a múltiples usuarios."""
    pass
```

---

#### 3.2 stats_service.py (54% → >85%)
**Tests a implementar (~6 tests):**

```python
# tests/api/test_stats_advanced.py

def test_get_global_stats_with_cache():
    """Stats globales usan cache correctamente."""
    pass

def test_get_global_stats_cache_invalidation():
    """Cache se invalida cuando cambian datos."""
    pass

def test_get_source_stats_aggregations():
    """Agregaciones SQL correctas por fuente."""
    pass

def test_get_source_stats_performance():
    """Queries optimizadas (sin N+1)."""
    pass

def test_stats_with_large_dataset():
    """Maneja datasets grandes (>1000 videos)."""
    pass

def test_stats_response_format():
    """Formato de respuesta cumple schema."""
    pass
```

---

#### 3.3 cache_service.py (66% → >85%)
**Tests a implementar (~5 tests):**

```python
# tests/services/test_cache_service_advanced.py

def test_cache_invalidation_pattern():
    """Invalidación por patrón (ej: stats:*)."""
    pass

def test_cache_ttl_expiration():
    """TTL expira correctamente."""
    pass

def test_cache_namespace_isolation():
    """Namespaces aislados correctamente."""
    pass

def test_cache_with_redis_down():
    """Degradación graceful si Redis cae."""
    pass

def test_cache_serialization_complex_types():
    """Serializa/deserializa tipos complejos."""
    pass
```

---

#### 3.4 downloader_service.py (72% → >85%)
**Tests a implementar (~4 tests):**

```python
# tests/services/test_downloader_service_advanced.py

def test_download_audio_cleanup_on_error():
    """Limpia archivos temporales en error."""
    pass

def test_download_audio_with_age_restriction():
    """Maneja videos con restricción de edad."""
    pass

def test_download_audio_with_geo_restriction():
    """Maneja videos geo-bloqueados."""
    pass

def test_download_concurrent_limit():
    """Limita descargas concurrentes."""
    pass
```

---

### FASE 4: Validación y Documentación (1h)

**Objetivo:** Confirmar >80% coverage y documentar

#### 4.1 Ejecutar suite completa
```bash
poetry run pytest --cov=src --cov-report=html --cov-report=term-missing
```

**Verificar:**
- [ ] Coverage total >80%
- [ ] Todos los tests pasan (0 failures)
- [ ] Suite ejecuta en <3 minutos
- [ ] Coverage de módulos críticos >85%

---

#### 4.2 Generar documentación

**Documentos a crear:**
1. ✅ `docs/test-coverage-baseline.md` - Estado inicial
2. ✅ `docs/test-strategy.md` - Este documento
3. ⏳ `docs/testing-guide.md` - Guía completa de testing
4. ⏳ `README.md` - Actualizar con badges

**Contenido de testing-guide.md:**
- Filosofía de testing del proyecto
- Cómo ejecutar tests
- Cómo escribir nuevos tests
- Estructura de fixtures
- Naming conventions
- AAA pattern (Arrange-Act-Assert)
- Mocking best practices
- Troubleshooting común

---

## 🧪 Principios de Testing

### 1. Tests Independientes
- Cada test es autónomo
- No dependen del orden de ejecución
- Usan fixtures para setup/teardown

### 2. Tests Rápidos
- Unit tests: <100ms por test
- Integration tests: <2s por test
- E2E tests: <10s por test
- Suite completa: <3 minutos

### 3. Tests Claros
- Nombres descriptivos: `test_<función>_<caso>_<resultado>`
- AAA pattern: Arrange → Act → Assert
- Un assert por concepto (múltiples asserts OK si son relacionados)

### 4. Tests Mantenibles
- DRY (Don't Repeat Yourself) con fixtures
- Evitar lógica compleja en tests
- Tests fáciles de leer = documentación viva

---

## 🛠️ Técnicas y Herramientas

### Fixtures (pytest)
```python
@pytest.fixture
def sample_video(db_session):
    """Video de prueba reutilizable."""
    video = Video(youtube_id="test123", title="Test")
    db_session.add(video)
    db_session.commit()
    return video
```

### Mocking (unittest.mock)
```python
@patch("src.services.telegram_service.Bot")
def test_send_message(mock_bot):
    mock_bot.send_message = AsyncMock()
    # ... test logic
```

### Parametrize (pytest)
```python
@pytest.mark.parametrize("duration,expected", [
    (60, "1:00"),
    (3661, "1:01:01"),
])
def test_format_duration(duration, expected):
    assert format_duration(duration) == expected
```

---

## 📈 Métricas de Calidad

### Coverage Targets
| Tipo | Target |
|------|--------|
| **Global** | >80% |
| **Servicios core** | >85% |
| **Repositories** | >90% |
| **Utils** | >70% |
| **Handlers** | >75% |

### Calidad de Tests
- [ ] 0 failures
- [ ] 0 warnings críticas
- [ ] 0 tests skipped (excepto marcados explícitamente)
- [ ] Tiempo ejecución <3min
- [ ] Sin tests flaky (intermitentes)

---

## 🚀 Próximos Pasos

1. ✅ Completar Fase 1 (estabilización)
2. ⏳ Implementar Fase 2 (módulos críticos)
3. ⏳ Implementar Fase 3 (servicios core)
4. ⏳ Completar Fase 4 (validación y docs)
5. ⏳ Integrar con CI/CD (Paso 25)

---

## 📚 Referencias

- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Guide](https://coverage.readthedocs.io/)
- [Testing Best Practices - Real Python](https://realpython.com/python-testing/)
- [Clean Architecture Testing](https://blog.cleancoder.com/uncle-bob/2017/05/05/TestDefinitions.html)

---

**Documento generado:** 2025-11-16
**Última actualización:** 2025-11-16
**Estado:** FASE 1 en progreso
