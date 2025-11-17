# Análisis de Coverage - Paso 24

**Fecha:** 17/11/2025
**Coverage actual:** 70.53%
**Coverage objetivo:** >80%
**Gap:** 9.47 puntos porcentuales

---

## 📊 Coverage Actual por Módulo

### 🔴 Prioridad Alta (Coverage <70%)

| Módulo | Coverage | Líneas sin cubrir | Prioridad | Estado |
|--------|----------|-------------------|-----------|--------|
| `src/services/youtube_scraper_service.py` | 0% | 91/91 | 🔴 CRÍTICA | Pendiente |
| `src/tasks/scraping.py` | 0% | 84/84 | 🔴 CRÍTICA | Pendiente |
| `src/services/output_validator.py` | 23% | 53/69 | 🔴 Alta | Pendiente |
| `src/tasks/video_processing.py` | 28% | 57/79 | 🔴 Alta | Pendiente |
| `src/tasks/distribute_summaries.py` | 46% | 53/98 | 🔴 Alta | Tiene errores |
| `src/repositories/summary_repository.py` | 53% | 52/111 | 🔴 Alta | Pendiente |
| `src/repositories/user_repository.py` | 57% | 15/35 | 🔴 Alta | Pendiente |
| `src/services/downloader_service.py` | 66% | 30/89 | 🟡 Media | Pendiente |
| `src/repositories/transcription_repository.py` | 67% | 7/21 | 🟡 Media | Pendiente |
| `src/services/transcription_service.py` | 69% | 29/94 | 🟡 Media | Tiene errores |

### 🟡 Prioridad Media (Coverage 70-79%)

| Módulo | Coverage | Líneas sin cubrir | Prioridad | Estado |
|--------|----------|-------------------|-----------|--------|
| `src/repositories/video_repository.py` | 76% | 19/80 | 🟡 Media | Casi completo |
| `src/services/summarization_service.py` | 79% | 26/124 | 🟡 Media | Casi completo |
| `src/services/cache_service.py` | 80% | 48/239 | 🟡 Media | Casi completo |

### 🟢 Coverage Aceptable (>80%)

| Módulo | Coverage | Estado |
|--------|----------|--------|
| `src/models/telegram_user.py` | 85% | ✅ Bien |
| `src/models/transcription.py` | 85% | ✅ Bien |
| `src/core/logging_config.py` | 87% | ✅ Bien |
| `src/core/celery_context.py` | 89% | ✅ Bien |
| `src/models/video.py` | 90% | ✅ Excelente |
| `src/services/prompts/__init__.py` | 90% | ✅ Excelente |
| `src/models/user.py` | 92% | ✅ Excelente |
| `src/services/video_processing_service.py` | 94% | ✅ Excelente |
| `src/models/summary.py` | 94% | ✅ Excelente |
| `src/core/config.py` | 95% | ✅ Excelente |
| `src/models/source.py` | 95% | ✅ Excelente |
| `src/repositories/telegram_user_repository.py` | 96% | ✅ Excelente |
| `src/services/input_sanitizer.py` | 98% | ✅ Excelente |
| `src/core/database.py` | 100% | ✅ Perfecto |
| `src/core/celery_app.py` | 100% | ✅ Perfecto |
| `src/core/metrics.py` | 100% | ✅ Perfecto |
| `src/repositories/base_repository.py` | 100% | ✅ Perfecto |
| `src/repositories/source_repository.py` | 100% | ✅ Perfecto |

---

## 🎯 Módulos Priorizados para Implementación

### 🔴 Prioridad 1: Módulos Críticos (0-50% coverage)

#### 1. **YouTubeScraperService** (0% - 91 líneas)
- **Razón:** Componente crítico del pipeline de scraping
- **Tests necesarios:** 6-8 tests
- **Áreas clave:**
  - Scraping de canales de YouTube
  - Extracción de metadata
  - Manejo de rate limits de YouTube API
  - Deduplicación de videos

#### 2. **Tasks: scraping.py** (0% - 84 líneas)
- **Razón:** Orquestador principal del scraping periódico
- **Tests necesarios:** 5-7 tests
- **Áreas clave:**
  - Tarea Celery de scraping
  - Integración con YouTubeScraperService
  - Manejo de errores y reintentos
  - Registro de scraping jobs

#### 3. **OutputValidator** (23% - 53 líneas sin cubrir)
- **Razón:** Seguridad crítica - valida respuestas del LLM
- **Tests necesarios:** 8-10 tests
- **Áreas clave:**
  - Validación de estructura JSON
  - Validación de longitud de resumen
  - Validación de keywords
  - Detección de contenido malicioso

#### 4. **Tasks: video_processing.py** (28% - 57 líneas sin cubrir)
- **Razón:** Orquestador del pipeline principal
- **Tests necesarios:** 7-9 tests
- **Áreas clave:**
  - Tarea Celery de procesamiento
  - Transiciones de estado
  - Manejo de errores
  - Limpieza de archivos temporales

#### 5. **Tasks: distribute_summaries.py** (46% - 53 líneas sin cubrir)
- **Razón:** Distribución a usuarios de Telegram
- **Tests necesarios:** 8-10 tests (7 errores actuales a corregir)
- **Áreas clave:**
  - Distribución a usuarios suscritos
  - Manejo de usuarios que bloquean bot
  - Rate limiting de Telegram
  - Deduplicación de envíos

### 🟡 Prioridad 2: Módulos Importantes (50-70% coverage)

#### 6. **SummaryRepository** (53% - 52 líneas sin cubrir)
- **Tests necesarios:** 10-12 tests
- **Áreas clave:**
  - Búsqueda full-text avanzada
  - Paginación cursor-based
  - Queries complejas con joins
  - Ranking de resultados

#### 7. **UserRepository** (57% - 15 líneas sin cubrir)
- **Tests necesarios:** 6-8 tests
- **Áreas clave:**
  - Creación de usuarios
  - Hash de passwords con bcrypt
  - Verificación de credenciales
  - Manejo de roles

#### 8. **DownloaderService** (66% - 30 líneas sin cubrir)
- **Tests necesarios:** 6-8 tests
- **Áreas clave:**
  - Descarga de audio con yt-dlp
  - Extracción de metadata
  - Manejo de errores (red, videos privados)
  - Limpieza de archivos temporales

#### 9. **TranscriptionRepository** (67% - 7 líneas sin cubrir)
- **Tests necesarios:** 5-6 tests
- **Áreas clave:**
  - CRUD de transcripciones
  - Relaciones con videos
  - Queries por idioma

#### 10. **TranscriptionService** (69% - 29 líneas sin cubrir)
- **Tests necesarios:** 6-8 tests (2 errores actuales a corregir)
- **Áreas clave:**
  - Transcripción con Whisper
  - Detección de idioma
  - Cache de modelo
  - Manejo de archivos de audio

### 🟢 Prioridad 3: Reforzar módulos casi completos (70-80%)

#### 11. **VideoRepository** (76% - 19 líneas sin cubrir)
- **Tests necesarios:** 4-5 tests adicionales
- **Áreas clave:**
  - Soft delete
  - Filtros por estado
  - Queries complejas

#### 12. **SummarizationService** (79% - 26 líneas sin cubrir)
- **Tests necesarios:** 5-6 tests adicionales
- **Áreas clave:**
  - Casos edge de LLM
  - Validación de output
  - Manejo de timeouts

#### 13. **CacheService** (80% - 48 líneas sin cubrir)
- **Tests necesarios:** 6-8 tests adicionales
- **Áreas clave:**
  - Operaciones de cache complejas
  - Invalidación
  - Expiración

---

## 📈 Estimación de Tests Necesarios

### Por Tipo

| Tipo de Test | Cantidad | Tiempo Estimado |
|--------------|----------|-----------------|
| **Servicios (unit)** | ~40 tests | 2.5 días |
| **Repositories (unit)** | ~40 tests | 1.5 días |
| **Tasks (unit)** | ~20 tests | 1.5 días |
| **Integración API** | ~15 tests | 1 día |
| **E2E Pipeline** | ~15 tests | 1.5 días |
| **TOTAL** | **~130 tests** | **8 días** |

### Por Prioridad

| Prioridad | Tests | Impacto en Coverage |
|-----------|-------|---------------------|
| 🔴 Alta | 60 tests | +8% coverage |
| 🟡 Media | 40 tests | +1.5% coverage |
| 🟢 Baja | 30 tests | +0.5% coverage |

---

## 🚨 Tests con Errores Actuales

### Errores a corregir antes de continuar

1. **API Videos Tests** (4 fallos)
   - `test_delete_video_success` - Problema de autenticación (401)
   - `test_delete_video_not_found` - Problema de autenticación (401)
   - `test_delete_video_already_deleted` - Problema de autenticación (401)
   - `test_process_video_invalid_state` - Problema de autenticación (401)

2. **Integration Tests** (3 fallos + 2 errores)
   - `test_metadata_completeness` - DownloaderService
   - `test_generate_summary_with_database` - SummarizationService
   - `test_generate_summary_duplicate_error` - SummarizationService
   - `test_transcribe_audio_success` - ERROR TranscriptionService
   - `test_transcribe_with_timestamps_success` - ERROR TranscriptionService

3. **Tasks Tests** (5 errores)
   - `test_distribute_to_subscribed_users_success` - TypeError
   - `test_skip_if_already_sent` - TypeError
   - `test_handle_user_blocked_bot` - TypeError
   - `test_no_users_subscribed` - TypeError
   - `test_telegram_rate_limit_retry` - TypeError

**Total de tests con problemas:** 12 (4 fallos + 7 errores + 1 fallo repository)

---

## 📋 Plan de Acción

### Fase 1: Corrección de Tests Existentes (Día 1)
- ✅ Corregir 4 tests de autenticación en API
- ✅ Corregir 5 tests de integración
- ✅ Corregir 7 tests de tasks

### Fase 2: Tests Unitarios Críticos (Días 2-4)
- ✅ YouTubeScraperService (6 tests)
- ✅ OutputValidator (8 tests)
- ✅ Tasks: scraping.py (7 tests)
- ✅ Tasks: video_processing.py (9 tests)
- ✅ Tasks: distribute_summaries.py (10 tests adicionales)

### Fase 3: Repositories (Días 5-6)
- ✅ SummaryRepository (12 tests)
- ✅ UserRepository (8 tests)
- ✅ TranscriptionRepository (6 tests)
- ✅ VideoRepository (5 tests adicionales)

### Fase 4: Servicios Restantes (Día 7)
- ✅ DownloaderService (8 tests)
- ✅ TranscriptionService (8 tests adicionales)
- ✅ SummarizationService (6 tests adicionales)

### Fase 5: Integración y E2E (Día 8)
- ✅ Tests de integración API (15 tests)
- ✅ Tests E2E pipeline (15 tests)

### Fase 6: Optimización y Documentación (Día 9)
- ✅ Optimización de suite (<2 min)
- ✅ Documentación (testing-guide.md)
- ✅ Configuración pytest.ini

---

## 🎯 Impacto Proyectado

### Coverage Proyectado por Módulo

| Módulo | Actual | Proyectado | Mejora |
|--------|--------|------------|--------|
| YouTubeScraperService | 0% | 85%+ | +85% |
| scraping.py | 0% | 80%+ | +80% |
| OutputValidator | 23% | 90%+ | +67% |
| video_processing.py | 28% | 85%+ | +57% |
| distribute_summaries.py | 46% | 85%+ | +39% |
| summary_repository.py | 53% | 90%+ | +37% |
| user_repository.py | 57% | 90%+ | +33% |
| downloader_service.py | 66% | 85%+ | +19% |
| transcription_service.py | 69% | 85%+ | +16% |

### Coverage Global Proyectado

**Actual:** 70.53%
**Proyectado:** 82-85%
**Mejora:** +11.5 - 14.5 puntos porcentuales

---

## ✅ Criterios de Éxito

- [ ] Coverage global >80%
- [ ] Todos los módulos críticos >80%
- [ ] 0 tests fallidos
- [ ] 0 tests con errores
- [ ] Suite completa <2 minutos
- [ ] Documentación completa

---

**Próximo paso:** Comenzar con Tarea 2 - Tests Unitarios de Servicios
