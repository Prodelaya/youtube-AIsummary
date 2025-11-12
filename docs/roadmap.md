# 🗺️ ROADMAP DETALLADO - IA MONITOR
**Versión:** 1.0
**Actualizado:** Octubre 2025
**Metodología:** Incremental con validación paso a paso

---

## 📖 ÍNDICE
- Visión General
- Fase 0: Planning & Setup (1 día)
- Fase 1: Infraestructura Base (2-3 días)
- Fase 2: Pipeline Core (1 semana)
- Fase 3: API REST + Bot Telegram (5-6 días)
- Fase 4: Workers Async (2-3 días)
- Fase 5: Observabilidad (2 días)
- Fase 6: Testing & CI (2 días)
- Fase 7: Deployment (2-3 días)
- Timeline Semanal
---

## 🎯 VISIÓN GENERAL

### Objetivo del Proyecto
Crear un agregador inteligente con bot de Telegram multi-usuario que automáticamente:
- Recopila contenidos sobre IA en desarrollo software (YouTube, RSS, podcasts)
- Transcribe audios usando Whisper (local, gratuito)
- Resume textos usando DeepSeek API (bajo coste, sin límites)
- Distribuye resúmenes personalizados vía Bot de Telegram interactivo
- Cada usuario elige sus canales y gestiona su historial

### Doble Propósito
- **Utilidad real:** Bot multi-usuario donde cada persona elige sus canales de interés
- **Portfolio profesional:** Demostrar backend Python moderno con IA funcional y arquitectura multi-usuario

### Stack Tecnológico
- **Backend:** FastAPI (sync endpoints) + PostgreSQL + Redis
- **Workers:** Celery para tareas en background (scraping, transcripción, distribución)
- **Bot:** python-telegram-bot con inline keyboards y commands interactivos
- **IA:** Whisper (transcripción local) + DeepSeek API (resúmenes)
- **DevOps:** Docker, GitHub Actions, Prometheus + Grafana

---

## 📋 FASE 0: PLANNING & SETUP (1 día)

### Paso 1: Documento de Arquitectura (Project Designer)
**¿Qué hacer?**
- Crear `docs/architecture.md` usando el prompt Project Designer
- Decisiones técnicas justificadas (Whisper local vs APIs de pago, DeepSeek vs ApyHub/LangChain - ADR-009, Celery vs BackgroundTasks)
- Diagrama Mermaid de arquitectura completa (componentes + flujos)
- Estructura de directorios definitiva
- Roadmap de features priorizadas por fases

**¿Por qué primero?**
- Define QUÉ construir y CÓMO antes de escribir una línea de código
- Evita refactors masivos posteriores (ej: cambiar de MongoDB a PostgreSQL en semana 3)
- Justifica decisiones técnicas ante reclutadores (portfolio = arquitectura pensada)
- Detecta dependencias críticas temprano (ej: limitaciones de APIs externas que motivaron migración a DeepSeek)

**Entregable:**
- `docs/architecture.md` completo con diagramas
- Stack técnico con tabla de pros/contras
- Flujos de procesamiento documentados

**Git:**
```bash
git commit -m "docs: add initial architecture document with diagrams"
```
**Nos da paso a:** Crear estructura del repositorio basada en arquitectura definida.

---

### Paso 2: Estructura del Repositorio
**¿Qué hacer?**
- Crear carpetas según arquitectura: `src/api/`, `src/services/`, `src/models/`, `src/repositories/`, `src/tasks/`, `tests/`
- Inicializar Git con `.gitignore` (Python, Docker, secretos)
- README básico con descripción, badges placeholders (CI, coverage)
- `.env.example` con template de variables (sin valores reales)
- `docs/ADR/` para Architecture Decision Records

**¿Por qué esta estructura?**
- Separación clara: API / Servicios / Datos (Clean Architecture)
- Tests desde día 1 = cultura de calidad
- `.env.example` documenta qué variables necesita el proyecto
- ADRs justifican decisiones importantes (por qué Whisper local, no Deepgram API)

**Entregable:**
- Carpetas vacías pero con `__init__.py`
- README con descripción del proyecto
- `.gitignore` configurado

**Git:**
```bash
git init
git add .
git commit -m "chore: initial project structure with Clean Architecture"
git remote add origin <tu-repo>
git push -u origin main
```
**Nos da paso a:** Configurar gestor de dependencias reproducible.

---

### Paso 3: Poetry Setup + Dependencias Base
**¿Qué hacer?**
- Inicializar Poetry con `poetry init`
- Instalar dependencias core: FastAPI, SQLAlchemy, Alembic, PostgreSQL driver, Redis, Celery
- Instalar dependencias IA: Whisper, yt-dlp (descarga YouTube), httpx (cliente HTTP async)
- Dev dependencies: pytest, black, ruff, mypy, pytest-cov

**¿Por qué ahora?**
- Dependencias fijadas en `poetry.lock` = reproducible en cualquier máquina
- Instalar todo de golpe evita conflictos de versiones después
- Poetry gestiona entornos virtuales automáticamente

**Entregable:**
- `pyproject.toml` con todas las dependencias
- `poetry.lock` generado

**Git:**
```bash
git add pyproject.toml poetry.lock
git commit -m "chore: add Poetry dependencies for FastAPI, Whisper, and testing"
```
**Nos da paso a:** Levantar infraestructura local (BD + cache).

---

## 🏗️ FASE 1: INFRAESTRUCTURA BASE (2-3 días)

### Paso 4: Docker Compose (Postgres + Redis)
**¿Qué hacer?**
- Crear `docker-compose.yml` con servicios: Postgres 15, Redis 7
- Configurar volúmenes para persistencia de datos
- Puertos expuestos: Postgres 5432, Redis 6379
- Variables de entorno para usuario/password de BD

**¿Por qué Docker?**
- BD lista en 1 comando (`docker-compose up -d`)
- Mismo entorno en dev/staging/prod (no "funciona en mi máquina")
- No contamina sistema local (se borra fácilmente)

**Validación:**
- `docker-compose up -d` arranca sin errores
- Conexión a Postgres exitosa con `psql`
- Redis responde a `redis-cli ping` con `PONG`

**Git:**
```bash
git commit -m "feat: add Docker Compose with Postgres and Redis"
```
**Nos da paso a:** Configurar variables de entorno de la aplicación.

---

### Paso 5: Config + Variables de Entorno
**¿Qué hacer?**
- Crear `src/core/config.py` usando Pydantic Settings
- Validar variables obligatorias: `DATABASE_URL`, `REDIS_URL`, `DEEPSEEK_API_KEY`
- `.env.example` con plantilla (este SÍ va a Git)
- `.env` real (este NO va a Git, usuario debe crearlo copiando el example)

**¿Por qué Pydantic Settings?**
- Validación automática al arrancar (si falta variable, app no inicia)
- Tipado fuerte (no strings mágicos)
- 12-factor app compliant (configuración fuera del código)

**Validación:**
- App falla si `.env` no existe (comportamiento esperado)
- App arranca correctamente con `.env` válido

**Git:**
```bash
git add src/core/config.py .env.example
git commit -m "feat: add configuration management with Pydantic Settings"
```
**Nos da paso a:** Crear API base funcional.

---

### Paso 6: FastAPI Base + Health Check
**¿Qué hacer?**
- Crear `src/api/main.py` con aplicación FastAPI mínima
- Endpoint `/health` que devuelve `{"status": "ok"}`
- Endpoint `/` que devuelve mensaje de bienvenida
- Configurar documentación automática en `/api/docs`

**¿Por qué health check?**
- Valida que FastAPI funciona correctamente
- Necesario para monitoreo futuro (Prometheus, Kubernetes probes)
- Primera victoria rápida (motivación para continuar)

**Validación:**
- `uvicorn src.api.main:app` arranca sin errores
- `curl localhost:8000/health` responde 200 OK
- Swagger UI accesible en `localhost:8000/api/docs`

**Test:**
- Crear `tests/test_health.py` con test del endpoint health
- `pytest tests/test_health.py -v` debe pasar

**Git:**
```bash
git commit -m "feat: add FastAPI base with health endpoint"
git commit -m "test: add health endpoint test"
```
**Nos da paso a:** Configurar ORM y sistema de migraciones.

---

### Paso 7: ORM + Migraciones (Alembic)
**¿Qué hacer?**
- Configurar SQLAlchemy `engine` y `sessionmaker` en `src/core/database.py`
- Inicializar Alembic con `alembic init migrations`
- Configurar `alembic.ini` para usar `DATABASE_URL` desde `.env`
- Crear primer modelo: `Source` (tabla de fuentes: YouTube channels, RSS feeds)
- Generar migración automática: `alembic revision --autogenerate`
- Aplicar migración: `alembic upgrade head`

**¿Por qué migraciones?**
- Schema de BD versionado (como Git pero para la base de datos)
- Rollback posible si algo falla (`alembic downgrade`)
- Colaboración sin romper datos de otros desarrolladores
- Historial de cambios en schema documentado

**Validación:**
- Tabla `sources` existe en Postgres
- Tabla `alembic_version` registra la migración
- `alembic current` muestra versión actual

**Git:**
```bash
git commit -m "feat: add SQLAlchemy ORM setup"
git commit -m "feat: add Alembic migrations"
git commit -m "feat: add Source model with first migration"
```
**Nos da paso a:** Implementar servicios core del pipeline.

---

## 🧩 FASE 2: PIPELINE CORE (1 semana)

### Paso 8: Integración DeepSeek (Resúmenes)
**¿Qué hacer?**
- Crear `src/services/summarization_service.py`
- Implementar método `summarize_text()` que llama a DeepSeek API
- Usar SDK de OpenAI (compatible con DeepSeek)
- Implementar sistema de prompts en `src/services/prompts/`
- Manejo de errores: timeout, respuestas inválidas

**¿Por qué primero?**
- Es el componente externo crítico del sistema
- Si DeepSeek está caído o cambia API, mejor descubrirlo YA
- Lo más rápido de validar (no requiere BD ni otros servicios)
- API síncrona simple (SDK compatible con OpenAI)

**Validación:**
- Test de integración que llama a API real con texto de prueba
- Resumen generado correctamente en español
- Sistema de prompts funciona correctamente

**Git:**
```bash
git commit -m "feat: add DeepSeek summarization service with OpenAI SDK"
git commit -m "feat: add prompt engineering system"
git commit -m "test: add DeepSeek integration test"
```
**Nos da paso a:** Implementar descarga de audios.

---

### Paso 9: Descarga de Audio (yt-dlp)
**¿Qué hacer?**
- Crear `src/services/downloader_service.py`
- Implementar `download_audio()` que descarga audio de YouTube en MP3
- Implementar `get_video_metadata()` para obtener info sin descargar
- Configurar carpeta temporal `/tmp/ia-monitor/downloads`
- Extraer mejor calidad de audio disponible

**¿Por qué después de DeepSeek?**
- No depende de DeepSeek (servicios aislados)
- Genera archivos que el siguiente paso (transcripción) consumirá

**Validación:**
- Descargar video test de 30 segundos funciona
- Archivo MP3 generado existe y pesa >10KB
- Metadata extraída correctamente (título, duración, autor)

**Git:**
```bash
git commit -m "feat: add YouTube audio downloader with yt-dlp"
git commit -m "test: add downloader service test with sample video"
```
**Nos da paso a:** Implementar transcripción local.

---

### Paso 10: Transcripción (Whisper Local)
**¿Qué hacer?**
- Crear `src/services/transcription_service.py`
- Cargar modelo Whisper (usar **base** para balance velocidad/precisión)
- Implementar `transcribe_audio()` que convierte MP3 a texto
- Soportar idioma español por defecto, configurable
- Implementar variante con **timestamps** (para features futuras)

**¿Por qué Whisper local?**
- Gratuito (vs Deepgram $0.006/min que escala rápido)
- Privacidad (audio no sale del servidor)
- Portfolio impresionante (demuestra manejo de modelos ML reales)
- Sin límites (procesar 1000 videos no cuesta nada)

**Validación:**
- Primera ejecución descarga modelo (2-3 min, normal)
- Transcripción de audio de 30s tarda <1 minuto
- Texto generado tiene sentido y está en español

**Git:**
```bash
git commit -m "feat: add Whisper transcription service"
git commit -m "test: add transcription test with sample audio"
```
**Nos da paso a:** Conectar todos los servicios en un pipeline.

---

### Paso 11: Modelos de BD Completos (✅ COMPLETADO)
**¿Qué hacer?**
- Crear modelo `Transcription` con relación 1:1 a Video
- Crear modelo `Summary` con relación 1:1 a Transcription
- Crear modelo `TelegramUser` con relación M:N a Source
- Generar y aplicar migraciones Alembic
- Actualizar `Video` model con relación a `Transcription`

**Estado:**
- ✅ Modelos creados con tipado completo: Source, Video, Transcription, Summary, TelegramUser
- ✅ Relaciones definidas (Video → Transcription → Summary)
- ✅ Tabla intermedia `user_source_subscriptions` para suscripciones
- ✅ Migración aplicada con índices GIN y full-text search
- ✅ Campos de tracking en Summary para Telegram
- ✅ Exports actualizados en `__init__.py`

**Git:**
```bash
# Ya commiteado:
feat(models): add Transcription and Summary models
feat(models): add TelegramUser model with M:N subscriptions
feat(db): add migration for all tables with relationships
```
**Nos da paso a:** Implementar Repository Pattern.

---

### Paso 12: Repository Pattern (✅ COMPLETADO)
**¿Qué hacer?**
- Crear `src/repositories/base_repository.py` genérico con TypeVar[T]
- Implementar CRUD síncrono: `create`, `get_by_id`, `list_all`, `update`, `delete`
- Crear `SourceRepository` con métodos específicos
- Crear `VideoRepository` con queries por estado
- Crear `TranscriptionRepository` con búsqueda por video
- Crear `SummaryRepository` con filtros y búsqueda full-text
- Crear `TelegramUserRepository` con queries de suscripciones

**¿Por qué síncronos?** (ADR-011)
- Celery workers son 99% del uso de BD (síncronos por diseño)
- API REST: <10 req/día (uso ocasional)
- Implementación más simple (2 días vs 4 días async)
- SQLAlchemy ORM funciona mejor en modo sync

**Estado:**
- ✅ BaseRepository genérico con TypeVar[T]
- ✅ 5 repositories especializados implementados
- ✅ Métodos de búsqueda avanzada (full-text, filtros, paginación)
- ✅ Exception handling personalizado

**Git:**
```bash
# Ya commiteado:
feat(repositories): add BaseRepository with generic CRUD
feat(repositories): add SourceRepository and VideoRepository
feat(repositories): add TranscriptionRepository and SummaryRepository
feat(repositories): add TelegramUserRepository
```
**Nos da paso a:** Servicios de negocio y API REST.

---

### Paso 13: Servicios de Negocio (✅ COMPLETADO)
**¿Qué hacer?**
- Implementar `VideoProcessingService` como orquestador del pipeline
- Integrar descarga, transcripción y resumen en flujo unificado
- Manejo de errores con excepciones personalizadas
- Tracking de estado de procesamiento

**Estado:**
- ✅ `DownloaderService` - descarga de audio con yt-dlp
- ✅ `TranscriptionService` - transcripción con Whisper
- ✅ `SummarizationService` - resúmenes con DeepSeek API
- ✅ `VideoProcessingService` - orquestador del pipeline completo

**Git:**
```bash
# Ya commiteado:
feat(services): add video processing orchestrator
feat(services): integrate downloader, transcription and summarization
```
**Nos da paso a:** Implementar API REST completa.

---

## 🌐 FASE 3: API REST + BOT TELEGRAM MULTI-USUARIO (5-6 días)

### Paso 14: API REST Completa (✅ COMPLETADO)
**Contexto:** Backend completo con 18 endpoints para gestión de videos, transcripciones, resúmenes y estadísticas.

**¿Qué hacer?**
- Crear schemas Pydantic v2 en `src/api/schemas/`
- Implementar `src/api/routes/videos.py` (10 endpoints):
  - CRUD completo de videos
  - Procesamiento asíncrono (encolar, reintentar)
  - Estadísticas por video
- Implementar `src/api/routes/transcriptions.py` (2 endpoints):
  - Listado paginado
  - Detalle de transcripción
- Implementar `src/api/routes/summaries.py` (4 endpoints):
  - Listado paginado con cursor
  - Detalle de resumen
  - Búsqueda full-text con ranking
  - Soft delete
- Implementar `src/api/routes/stats.py` (2 endpoints):
  - Estadísticas globales del sistema
  - Estadísticas por fuente
- Configurar dependency injection para repos
- Exception handlers globales
- Metadata OpenAPI enriquecida

**Estado:**
- ✅ **18 endpoints implementados y documentados**
- ✅ Schemas Pydantic v2 con validación
- ✅ Paginación cursor-based
- ✅ Exception handlers globales
- ✅ OpenAPI docs con ejemplos y descripciones
- ✅ Dependency injection para repositories

**Git:**
```bash
# Ya commiteado:
feat(api): add videos endpoints with CRUD and processing
feat(api): add transcriptions endpoints
feat(api): add summaries endpoints with full-text search
feat(api): add stats endpoints
test(api): add comprehensive API test suite
```
**Nos da paso a:** Implementar Bot de Telegram multi-usuario.

---

### Paso 15: Bot de Telegram - Setup Básico (✅ COMPLETADO)
**¿Qué hacer?**
- Instalar `python-telegram-bot` con Poetry
- Crear `src/bot/telegram_bot.py` con configuración básica
- Implementar command `/start` con mensaje de bienvenida
- Implementar command `/help` con lista de comandos
- Registrar usuario automáticamente en `/start` (vía TelegramUserRepository)
- Configurar webhook o polling según entorno

**¿Por qué primero?**
- Valida que bot funciona antes de añadir complejidad
- Configura infraestructura básica (token, permisos)
- Primera interacción con usuarios

**Estado:**
- ✅ `python-telegram-bot v22.5` instalado
- ✅ Bot principal configurado en modo polling
- ✅ Handler `/start` con registro automático de usuarios
- ✅ Handler `/help` con lista de comandos
- ✅ Error handler global con logging estructurado
- ✅ 6 tests unitarios (todos pasan)
- ✅ Bot validado en Telegram (@yt_IAinformer_bot)

**Archivos creados:**
- `src/bot/__init__.py`
- `src/bot/telegram_bot.py` (154 líneas)
- `src/bot/handlers/start.py` (136 líneas)
- `src/bot/handlers/help.py` (49 líneas)
- `tests/bot/conftest.py` (127 líneas)
- `tests/bot/test_handlers.py` (6 tests)

**Decisiones técnicas:**
- Uso de `asyncio.to_thread()` para bridge async/sync (handlers → repositories)
- Polling mode para desarrollo, infraestructura lista para webhook
- Registro idempotente de usuarios (ejecutar `/start` 2 veces no duplica)

**Git:**
```bash
git commit -m "feat(bot): add telegram bot basic setup with polling mode"
git commit -m "feat(bot): add /start handler with automatic user registration"
git commit -m "feat(bot): add /help handler with command list"
git commit -m "test(bot): add comprehensive handler tests (6 tests)"
git commit -m "chore: add python-telegram-bot dependency"
```
**Nos da paso a:** Commands interactivos de suscripciones.

---

### Paso 16: Bot de Telegram - Suscripciones Interactivas
**¿Qué hacer?**
- Implementar command `/sources` con inline keyboard
- Mostrar lista de canales con botones ✅/❌ (suscrito/no suscrito)
- Implementar callback_query handler para toggle de suscripciones
- Actualizar teclado dinámicamente tras cada toggle
- Consumir API interna para obtener sources y gestionar suscripciones

**¿Por qué inline keyboards?**
- UX superior (botones vs escribir comandos)
- Feedback visual inmediato (✅/❌)
- Reduce errores del usuario (no tipear nombres de canales)

**Validación:**
- `/sources` muestra teclado con canales disponibles
- Click en botón actualiza suscripción en BD
- Teclado se actualiza reflejando nuevo estado

**Git:**
```bash
git commit -m "feat(bot): add /sources command with inline keyboard"
git commit -m "feat(bot): add subscription toggle callback handlers"
git commit -m "test(bot): add subscription toggle tests"
```
**Nos da paso a:** Commands de consulta de histórico.

---

### Paso 17: Bot de Telegram - Historial y Búsqueda
**¿Qué hacer?**
- Implementar command `/recent` — Últimos 10 resúmenes de canales suscritos
- Implementar command `/search <query>` — Buscar en histórico por keyword
- Formatear mensajes con:
  - 📹 Título del video
  - 🔗 Link de YouTube
  - ⏱️ Duración
  - 🏷️ Tags (#FastAPI #Python)
  - 📝 Resumen
- Añadir botón inline "Reenviar" por resumen
- Consumir API interna para queries filtradas

**¿Por qué estos commands?**
- `/recent` = acceso rápido a últimas novedades
- `/search` = recuperar información antigua fácilmente
- Formato enriquecido = mensajes útiles y visualmente claros

**Validación:**
- `/recent` muestra sólo resúmenes de canales suscritos
- `/search FastAPI` encuentra resúmenes relevantes
- Links de YouTube funcionan correctamente
- Botón "Reenviar" reenvia el mensaje

**Git:**
```bash
git commit -m "feat(bot): add /recent command with formatted messages"
git commit -m "feat(bot): add /search command with keyword filtering"
git commit -m "test(bot): add history and search tests"
```
**Nos da paso a:** Worker de distribución personalizada.

---

### Paso 18: Worker de Distribución Personalizada (ADR-010)
**¿Qué hacer?**
- Crear `src/tasks/distribute_summaries.py`
- Implementar tarea Celery `distribute_summary(summary_id: str)`
- Lógica:
  1. Obtener resumen de BD
  2. Consultar usuarios suscritos al canal (M:N query)
  3. Para cada usuario suscrito:
     - Formatear mensaje con 📹 título, 🔗 link, 📝 resumen
     - Enviar vía Bot API
     - Registrar `telegram_message_id` en BD
  4. Actualizar `summary.sent_to_telegram = True`
- Manejo de errores: reintentar si falla envío

**¿Por qué worker separado?**
- Envío a N usuarios puede tardar (rate limits de Telegram)
- No bloquea pipeline de transcripción/resumen
- Reintentos automáticos si usuario tiene bot bloqueado

**Validación:**
- Resumen generado se envía solo a usuarios suscritos al canal
- Campo `telegram_message_ids` se actualiza correctamente
- Bot no envía duplicados

**Git:**
```bash
git commit -m "feat(worker): add personalized distribution to Telegram users"
git commit -m "test(worker): add distribution tests with mock users"
```
**Nos da paso a:** Sistema de rate limiting para API de resúmenes.

---

## ⚡ FASE 4: WORKERS ASYNC (2-3 días)

### Paso 19: Celery Setup
**¿Qué hacer?**
- Configurar Celery en `src/core/celery_app.py` con Redis como broker
- Crear tarea `src/tasks/process_content_task.py` que ejecuta el pipeline completo
- Configurar Celery Beat para tareas programadas (scraping periódico de fuentes)
- Script de inicio de worker: `celery -A src.core.celery_app worker`

**¿Por qué Celery?**
- Procesamiento async = API responde inmediato, trabajo en background
- Transcripción de 1 video tarda 5-10 min (no puede bloquear endpoint HTTP)
- Reintentos automáticos si falla
- Escalable (múltiples workers en paralelo)

**Validación:**
- Worker arranca sin errores
- Tarea encolada se ejecuta correctamente
- Logs muestran progreso del procesamiento

**Git:**
```bash
git commit -m "feat: add Celery configuration with Redis broker"
git commit -m "feat: add process_content async task"
```
**Nos da paso a:** Automatizar procesamiento periódico.

---

### Paso 20: Jobs Programados (Celery Beat)
**¿Qué hacer?**
- Configurar Celery Beat scheduler
- Crear tarea `sync_sources_task.py` que:
  - Consulta fuentes activas en BD
  - Busca nuevos contenidos (últimos videos de canal YouTube, nuevos posts de RSS)
  - Encola procesamiento de contenidos nuevos
- Programar ejecución: cada 6 horas

**¿Por qué automatización?**
- Sistema autónomo = sin intervención manual
- Mantiene resúmenes actualizados automáticamente
- Demuestra orquestación de workers (punto fuerte en portfolio)

**Validación:**
- Beat scheduler arranca y programa tareas
- Tarea se ejecuta en horario configurado
- Nuevos contenidos detectados y procesados

**Git:**
```bash
git commit -m "feat: add Celery Beat for scheduled tasks"
git commit -m "feat: add sync_sources periodic task"
```
**Nos da paso a:** Implementar monitoreo y observabilidad.

---

## 📊 FASE 5: OBSERVABILIDAD (2 días)

### Paso 21: Logging Estructurado
**¿Qué hacer?**
- Configurar **structlog** para logs estructurados
- Logs en formato JSON con campos: timestamp, level, message, context
- Diferentes niveles por entorno: DEBUG en dev, INFO en prod
- Logs de cada servicio identificados claramente
- Rotar logs diariamente, mantener últimos 7 días

**¿Por qué logging estructurado?**
- Debuggear producción sin logs = adivinar
- JSON logs = fácil de parsear con herramientas (Loki, ELK)
- Context enriquecido (source_id, duration, etc.) ayuda a troubleshooting

**Validación:**
- Logs generados en formato JSON válido
- Diferentes servicios loggean correctamente
- Rotación funciona (archivos por día)

**Git:**
```bash
git commit -m "feat: add structured logging with structlog"
```
**Nos da paso a:** Agregar métricas para monitoreo.

---

### Paso 22: Métricas (Prometheus)
**¿Qué hacer?**
- Instalar `prometheus-client` para Python
- Exponer endpoint `/metrics` en FastAPI
- Métricas custom:
  - `summaries_generated_total` (contador)
  - `transcription_duration_seconds` (histograma)
  - `deepseek_api_calls_total` (contador)
  - `pipeline_errors_total` (contador por tipo)
- Configurar scraping de Prometheus en `docker-compose.yml`

**¿Por qué métricas?**
- Detectar problemas antes que usuarios se quejen
- Graficar rendimiento en Grafana
- SLOs medibles (ej: 95% de transcripciones <10min)

**Validación:**
- Endpoint `/metrics` expone métricas en formato Prometheus
- Prometheus scrapea métricas correctamente
- Valores se actualizan en tiempo real

**Git:**
```bash
git commit -m "feat: add Prometheus metrics instrumentation"
git commit -m "feat: add Prometheus to Docker Compose"
```
**Nos da paso a:** Visualizar métricas en dashboard.

---

### Paso 23: Grafana Dashboard
**¿Qué hacer?**
- Agregar Grafana a `docker-compose.yml`
- Configurar datasource Prometheus
- Crear dashboard con paneles:
  - Resúmenes generados (últimas 24h)
  - Duración promedio de transcripción
  - Rate de errores del pipeline

**¿Por qué Grafana?**
- Visualización clara de salud del sistema
- Alertas visuales (ej: errores >10% = panel rojo)
- Portfolio impresionante (no solo código, también ops)

**Validación:**
- Dashboard accesible en `localhost:3000`
- Paneles muestran datos reales
- Gráficos se actualizan automáticamente

**Git:**
```bash
git commit -m "feat: add Grafana dashboard for system metrics"
```
**Nos da paso a:** Implementar suite de tests completa.

---

## ✅ FASE 6: TESTING & CI/CD (2 días)

### Paso 24: Suite de Tests Completa
**¿Qué hacer?**
- Tests unitarios en `tests/unit/` para servicios y repositories
- Tests de integración en `tests/integration/` para API y BD
- Tests E2E en `tests/e2e/` para pipeline completo
- Configurar fixtures pytest para datos de prueba
- Objetivo: >80% de cobertura en lógica crítica

**¿Por qué cobertura alta?**
- Sin tests, cada cambio es ruleta rusa
- Tests = confianza para refactorizar
- Coverage >80% = señal de calidad profesional

**Validación:**
- `pytest tests/ -v` todos los tests pasan
- `pytest --cov=src` muestra cobertura >80%
- Tests rápidos (<2 min total)

**Git:**
```bash
git commit -m "test: add comprehensive test suite with >80% coverage"
```
**Nos da paso a:** Automatizar tests con CI.

---

### Paso 25: GitHub Actions (CI/CD)
**¿Qué hacer?**
- Crear `.github/workflows/test.yml`:
  - Trigger en `push` y `pull_request`
  - Setup Python 3.11 + Poetry
  - Levantar Postgres y Redis con `services`
  - Ejecutar `pytest` con coverage
  - Fallar si coverage <80%
- Crear `.github/workflows/lint.yml`:
  - Black, ruff, mypy
  - Fallar si hay errores de formato o tipado

**¿Por qué CI automatizado?**
- Previene merges que rompen tests
- Code review automático de formato
- Badge verde en README = proyecto mantenido

**Validación:**
- Push a rama trigger workflows
- Workflows pasan con código actual
- Badge en README muestra estado

**Git:**
```bash
git commit -m "ci: add GitHub Actions for tests and linting"
```
**Nos da paso a:** Preparar deployment a producción.

---

## 🚀 FASE 7: DEPLOYMENT (2-3 días)

### Paso 26: Dockerfile Optimizado
**¿Qué hacer?**
- Crear Dockerfile multi-stage (builder + runtime)
- Stage 1: Instalar dependencias con Poetry
- Stage 2: Copiar solo lo necesario (sin dev dependencies)
- Usuario no-root por seguridad
- Health check integrado en container

**¿Por qué multi-stage?**
- Imagen final más pequeña (500MB vs 2GB)
- Menos superficie de ataque (sin compiladores)
- Build cache eficiente

**Validación:**
- `docker build -t ia-monitor .` exitoso
- `docker run ia-monitor` arranca correctamente
- Imagen <600MB

**Git:**
```bash
git commit -m "feat: add optimized multi-stage Dockerfile"
```
**Nos da paso a:** Orquestar todos los servicios.

---

### Paso 27: Docker Compose Producción
**¿Qué hacer?**
- Crear `docker-compose.prod.yml` con todos los servicios:
  - API (FastAPI)
  - Worker (Celery worker)
  - Beat (Celery scheduler)
  - Postgres (con volumen persistente)
  - Redis
  - Prometheus
  - Grafana
- Configurar restart policies
- Límites de recursos (CPU, RAM)

**¿Por qué separar dev y prod?**
- Dev usa hot-reload, prod no
- Prod tiene health checks y limits
- Prod usa secretos desde variables, no `.env`

**Validación:**
- `docker-compose -f docker-compose.prod.yml up -d` levanta todo
- Todos los servicios saludables
- API accesible desde fuera del container

**Git:**
```bash
git commit -m "feat: add production Docker Compose configuration"
```
**Nos da paso a:** Scripts de deployment.

---

### Paso 28: Scripts de Deployment
**¿Qué hacer?**
- Crear `scripts/deploy.sh` que:
  - Pull últimos cambios de Git
  - Build nueva imagen Docker
  - Stop containers antiguos
  - Start nuevos containers
  - Health check post-deployment
  - Rollback automático si falla
- Crear `scripts/backup_db.sh` para backups automáticos
- Configurar `cron` job para backups diarios

**¿Por qué scripts?**
- Deployment manual = errores humanos
- Scripts = reproducible y documentado
- Rollback automático = recovery rápido

**Validación:**
- Script ejecuta sin errores
- Deployment se completa en <5 minutos
- Rollback funciona si se simula error

**Git:**
```bash
git commit -m "feat: add deployment and backup scripts"
```
**Nos da paso a:** Automatizar deployment.

---

### Paso 29: CD Automático (GitHub Actions)
**¿Qué hacer?**
- Crear `.github/workflows/deploy.yml`:
  - Trigger solo en push a `main`
  - Ejecutar después de tests exitosos
  - SSH a servidor de producción
  - Ejecutar script de deployment
  - Notificar en Slack/Discord si falla

**¿Por qué CD?**
- Push a main = deployment automático
- Sin intervención manual
- Faster time to production

**Validación:**
- Merge a `main` trigger deployment
- Cambios visibles en producción en <10 minutos
- Notificación recibida

**Git:**
```bash
git commit -m "ci: add continuous deployment workflow"
```
**Nos da paso a:** Documentación final.

---

### Paso 30: Documentación Final
**¿Qué hacer?**
- README completo con:
  - Descripción del proyecto y valor
  - Arquitectura (diagrama)
  - Instalación local paso a paso
  - Endpoints API documentados
  - Decisiones técnicas importantes (links a ADRs)
  - Badges (CI status, coverage, license)
- Actualizar `docs/ADR/` con decisiones finales
- Screenshots de Grafana dashboard
- Video demo de 2 minutos (opcional pero impresionante)

**¿Por qué documentación curada?**
- Onboarding de recruiters en <5 minutos
- Proyecto sin docs = proyecto amateur
- ADRs demuestran pensamiento arquitectónico

**Git:**
```bash
git commit -m "docs: complete README with architecture and setup guide"
git commit -m "docs: finalize ADRs for key technical decisions"
```

---

## 📅 TIMELINE SEMANAL

### ✅ Semana 1: Fundación (COMPLETADA)
- **Lunes:** Architecture doc + Git setup + Poetry ✅
- **Martes:** Docker Compose + Config + FastAPI base ✅
- **Miércoles:** ORM + Migraciones + Source model ✅
- **Jueves:** DeepSeek integration + Tests ✅
- **Viernes:** Downloader service + Whisper setup ✅

### ✅ Semana 2: Pipeline Completo + Modelos (COMPLETADA)
- **Lunes:** Transcription service + Pipeline orchestrator ✅
- **Martes:** Modelos BD completos (Video, Transcription, Summary, TelegramUser) ✅
- **Miércoles:** Repository Pattern completo (Base + 5 especializados) ✅
- **Jueves:** Servicios de negocio (VideoProcessingService) ✅
- **Viernes:** Schemas Pydantic v2 + API base ✅

### ✅ Semana 3: API REST Completa (COMPLETADA)
- **Lunes:** Endpoints Videos (10 endpoints CRUD + processing) ✅
- **Martes:** Endpoints Transcriptions y Summaries (6 endpoints) ✅
- **Miércoles:** Endpoints Stats (2 endpoints) + Exception handlers ✅
- **Jueves:** OpenAPI metadata + Tests API ✅
- **Viernes:** Refinamiento y documentación API ✅

### 📍 Semana 4: Bot Telegram Multi-Usuario (EN PROGRESO)
- **Lunes:** Bot - Setup básico + /start + /help ✅
- **Martes:** Bot - Suscripciones interactivas con inline keyboards ← 📍 AQUÍ ESTAMOS
- **Miércoles:** Bot - Historial y búsqueda (/recent, /search)
- **Jueves:** Worker de distribución personalizada (ADR-010)
- **Viernes:** Logging estructurado

### Semana 5: Observabilidad & Testing
- **Lunes:** Métricas Prometheus + Monitoreo de costos DeepSeek
- **Martes:** Dashboard Grafana completo
- **Miércoles:** Suite de tests completa (>80% coverage)
- **Jueves:** CI con GitHub Actions
- **Viernes:** Dockerfile optimizado

### Semana 6: Deployment & Docs
- **Lunes:** Dockerfile + Docker Compose prod
- **Martes:** Scripts de deployment + Backups
- **Miércoles:** CD automático + Validación
- **Jueves:** Documentación final + ADRs
- **Viernes:** Optimizaciones + Demo video

**Total:** ~5 semanas trabajando 3-4h/día
---

## ✅ REGLAS DE ORO

### 1. Commits Pequeños y Descriptivos
- ❌ `git commit -m "todo listo"`
- ✅ `git commit -m "feat(api): add summaries endpoint with pagination"`

### 2. Tests ANTES de Merge
- Cada feature debe tener tests antes de merge a main
- Coverage nunca debe bajar del 80%

### 3. Documentación Sincronizada
- README siempre actualizado con features nuevas
- ADRs para decisiones importantes

### 4. Branch Strategy
```text
main              ← Solo código funcional + tests
  ├─ feat/Deepseek-integration
  ├─ feat/whisper-transcription
  └─ feat/celery-workers
```

### 5. Validación Paso a Paso
- No avanzar al siguiente paso sin validar el actual
- "Funciona en mi máquina" no es suficiente (Docker soluciona esto)

---

¡Éxito con el proyecto! 🚀
