# 🗺️ ROADMAP DETALLADO - IA MONITOR
**Versión:** 1.0  
**Actualizado:** Octubre 2025  
**Metodología:** Incremental con validación paso a paso

---

## 📖 ÍNDICE
- Visión General
- Fase 0: Planning & Setup
- Fase 1: Infraestructura Base
- Fase 2: Pipeline Core
- Fase 3: API REST
- Fase 4: Workers Async
- Fase 5: Observabilidad
- Fase 6: Testing & CI
- Fase 7: Deployment
- Timeline Semanal

---

## 🎯 VISIÓN GENERAL

### Objetivo del Proyecto
Crear un agregador inteligente que automáticamente:
- Recopila contenidos sobre IA en desarrollo software (YouTube, RSS, podcasts)
- Transcribe audios usando Whisper (local, gratuito)
- Resume textos usando ApyHub API (10 llamadas/día gratis)
- Clasifica y expone resúmenes vía API REST y Telegram

### Doble Propósito
- **Utilidad real:** Mantenerse informado sobre novedades en IA  
- **Portfolio profesional:** Demostrar backend Python moderno con IA funcional

### Stack Tecnológico
- **Backend:** FastAPI (async) + PostgreSQL + Redis  
- **Workers:** Celery para tareas en background  
- **IA:** Whisper (transcripción local) + ApyHub API (resúmenes)  
- **DevOps:** Docker, GitHub Actions, Prometheus + Grafana

---

## 📋 FASE 0: PLANNING & SETUP (1 día)

### Paso 1: Documento de Arquitectura (Project Designer)
**¿Qué hacer?**
- Crear `docs/architecture.md` usando el prompt Project Designer
- Decisiones técnicas justificadas (Whisper local vs APIs de pago, ApyHub vs LangChain, Celery vs BackgroundTasks)
- Diagrama Mermaid de arquitectura completa (componentes + flujos)
- Estructura de directorios definitiva
- Roadmap de features priorizadas por fases

**¿Por qué primero?**
- Define QUÉ construir y CÓMO antes de escribir una línea de código
- Evita refactors masivos posteriores (ej: cambiar de MongoDB a PostgreSQL en semana 3)
- Justifica decisiones técnicas ante reclutadores (portfolio = arquitectura pensada)
- Detecta dependencias críticas temprano (ej: límite de 10 llamadas/día en ApyHub)

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
- Validar variables obligatorias: `DATABASE_URL`, `REDIS_URL`, `APYHUB_TOKEN`
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

### Paso 8: Integración ApyHub (Resúmenes)
**¿Qué hacer?**
- Crear `src/services/summarization_service.py`
- Implementar método `summarize_text()` que llama a ApyHub API
- Implementar método `get_summary_status()` para consultar resultado del job
- Usar **tenacity** para reintentos exponenciales (3 intentos máx.)
- Manejo de errores: rate limit, timeout, respuestas inválidas

**¿Por qué primero?**
- Es el componente externo crítico del sistema
- Si ApyHub está caído o cambia API, mejor descubrirlo YA
- Lo más rápido de validar (no requiere BD ni otros servicios)

**Validación:**
- Test de integración que llama a API real con texto de prueba
- Resumen generado correctamente en español
- Reintentos funcionan ante fallos temporales

**Git:**
```bash
git commit -m "feat: add ApyHub summarization service with retry logic"
git commit -m "test: add ApyHub integration test"
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

**¿Por qué después de ApyHub?**
- No depende de ApyHub (servicios aislados)
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

### Paso 11: Orquestador del Pipeline
**¿Qué hacer?**
- Crear `src/services/content_processor.py`
- Implementar `process_youtube_url()` que orquesta: **descarga → transcripción → resumen → guardar en BD**
- Manejar limpieza de archivos temporales
- Guardar transcripciones y resúmenes en BD vía repositories
- Polling simple para esperar resultado de ApyHub (mejorar con Celery después)

**¿Por qué orquestador?**
- Conecta los 3 servicios aislados (downloader, transcriber, summarizer)
- Un solo punto de entrada para el flujo completo
- Fácil de testear (mock cada servicio individual)
- Centraliza lógica de *error handling*

**Validación:**
- Test E2E: URL de YouTube → resumen guardado en BD
- Pipeline completo tarda ~5-10 minutos (esperado para Whisper)
- Archivos temporales eliminados correctamente

**Git:**
```bash
git commit -m "feat: add ContentProcessor orchestrator for full pipeline"
git commit -m "test: add end-to-end pipeline integration test"
```
**Nos da paso a:** Exponer funcionalidad vía API REST.

---

## 🌐 FASE 3: API REST (3-4 días)

### Paso 12: Modelos de BD Completos
**¿Qué hacer?**
- Crear modelo `Transcription` con campos: `id`, `source_id`, `text`, `audio_path`, `duration`, `language`
- Crear modelo `Summary` con campos: `id`, `transcription_id`, `summary_text`, `metadata`, `tags`
- Definir relaciones SQLAlchemy: `Source 1→N Transcriptions`, `Transcription 1→N Summaries`
- Generar y aplicar migraciones Alembic

**¿Por qué ahora?**
- Necesitamos persistir resultados del pipeline
- Relaciones bien definidas facilitan queries después
- Migraciones versionan cambios en schema

**Validación:**
- Tablas `transcriptions` y `summaries` existen en BD
- Relaciones funcionan (foreign keys correctas)

**Git:**
```bash
git commit -m "feat: add Transcription and Summary models with relationships"
git commit -m "feat: add migration for transcriptions and summaries tables"
```
**Nos da paso a:** Implementar capa de acceso a datos.

---

### Paso 13: Repository Pattern
**¿Qué hacer?**
- Crear `src/repositories/base_repository.py` con operaciones CRUD genéricas
- Implementar `SummaryRepository` extendiendo `BaseRepository`
- Implementar `TranscriptionRepository` con métodos específicos
- Métodos principales: `create`, `get_by_id`, `list_all`, `delete`
- Métodos personalizados: `get_recent_summaries`, `get_by_source`

**¿Por qué Repository Pattern?**
- Abstrae acceso a datos (cambiar de Postgres a otro DB = solo cambiar repos)
- Queries complejas centralizadas
- Fácil de testear con mocks
- Reutilizable (un repo, muchos servicios)

**Validación:**
- Tests unitarios de cada método del repository
- Operaciones CRUD funcionan correctamente

**Git:**
```bash
git commit -m "feat: add Repository pattern with base class"
git commit -m "feat: add SummaryRepository and TranscriptionRepository"
git commit -m "test: add repository unit tests"
```
**Nos da paso a:** Crear endpoints REST.

---

### Paso 14: Endpoints REST
**¿Qué hacer?**
- Crear **schemas Pydantic** en `src/api/schemas/` para request/response
- Implementar rutas en `src/api/routes/summaries.py`:
  - `GET /api/v1/summaries` — Listar resúmenes recientes
  - `GET /api/v1/summaries/{id}` — Detalle de resumen específico
- Implementar rutas en `src/api/routes/sources.py`:
  - `POST /api/v1/sources` — Registrar fuente nueva (YouTube channel, RSS)
  - `GET /api/v1/sources` — Listar fuentes activas
- Registrar routers en `main.py`

**¿Por qué estos endpoints?**
- Listar resúmenes = funcionalidad core visible
- Gestión de fuentes = permite alimentar el sistema
- Base para frontend o Telegram bot después

**Validación:**
- Swagger UI muestra todos los endpoints
- Tests de integración para cada endpoint
- Respuestas correctas con datos reales de BD

**Git:**
```bash
git commit -m "feat: add Pydantic schemas for API responses"
git commit -m "feat: add summaries REST endpoints"
git commit -m "feat: add sources REST endpoints"
git commit -m "test: add API integration tests"
```
**Nos da paso a:** Procesar tareas pesadas en background.

---

## ⚡ FASE 4: WORKERS ASYNC (2-3 días)

### Paso 15: Celery Setup
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

### Paso 16: Jobs Programados (Celery Beat)
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

### Paso 17: Logging Estructurado
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

### Paso 18: Métricas (Prometheus)
**¿Qué hacer?**
- Instalar `prometheus-client` para Python
- Exponer endpoint `/metrics` en FastAPI
- Métricas custom:
  - `summaries_generated_total` (contador)
  - `transcription_duration_seconds` (histograma)
  - `apyhub_api_calls_total` (contador)
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

### Paso 19: Grafana Dashboard
**¿Qué hacer?**
- Agregar Grafana a `docker-compose.yml`
- Configurar datasource Prometheus
- Crear dashboard con paneles:
  - Resúmenes generados (últimas 24h)
  - Duración promedio de transcripción
  - Rate de errores del pipeline
  - Uso de API ApyHub (llamadas restantes del día)

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

### Paso 20: Suite de Tests Completa
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

### Paso 21: GitHub Actions (CI/CD)
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

### Paso 22: Dockerfile Optimizado
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

### Paso 23: Docker Compose Producción
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

### Paso 24: Scripts de Deployment
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

### Paso 25: CD Automático (GitHub Actions)
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

### Paso 26: Documentación Final
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

### Semana 1: Fundación
- **Lunes:** Architecture doc + Git setup + Poetry
- **Martes:** Docker Compose + Config + FastAPI base
- **Miércoles:** ORM + Migraciones + Source model
- **Jueves:** ApyHub integration + Tests
- **Viernes:** Downloader service + Whisper setup

### Semana 2: Pipeline & API
- **Lunes:** Transcription service + Pipeline orchestrator
- **Martes:** Modelos BD completos + Repositories
- **Miércoles:** API REST endpoints + Schemas
- **Jueves:** Tests de integración API
- **Viernes:** Celery setup + Worker tasks

### Semana 3: Ops & Quality
- **Lunes:** Celery Beat + Jobs programados
- **Martes:** Logging + Prometheus metrics
- **Miércoles:** Grafana dashboard
- **Jueves:** Suite de tests completa + CI
- **Viernes:** Dockerfile + Docker Compose prod

### Semana 4: Deployment & Docs
- **Lunes:** Scripts de deployment + Backups
- **Martes:** CD automático + Validación
- **Miércoles:** Documentación final + ADRs
- **Jueves:** Optimizaciones + Pulido
- **Viernes:** Demo video + Publicación

**Total:** ~4 semanas trabajando 3-4h/día

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
  ├─ feat/apyhub-integration
  ├─ feat/whisper-transcription
  └─ feat/celery-workers
```

### 5. Validación Paso a Paso
- No avanzar al siguiente paso sin validar el actual
- "Funciona en mi máquina" no es suficiente (Docker soluciona esto)

---

¡Éxito con el proyecto! 🚀
