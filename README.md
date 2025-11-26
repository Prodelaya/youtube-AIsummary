# 🎓 YouTube AI Summary - Proyecto Didáctico de Arquitectura Backend Profesional

> **⚠️ NOTA IMPORTANTE:** Este proyecto es **intencionadamente overengineered** como proceso didáctico de aprendizaje. Si buscas una solución simple para resumir vídeos de YouTube, este no es el proyecto adecuado. Este repositorio está archivado como portafolio educativo.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-177+-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-80%25+-success.svg)](htmlcov/)

---

## 📋 Tabla de Contenidos

- [Sobre Este Proyecto](#-sobre-este-proyecto)
- [Objetivos de Aprendizaje](#-objetivos-de-aprendizaje)
- [Tecnologías y Herramientas](#-tecnologías-y-herramientas)
- [Arquitectura](#-arquitectura)
- [Características Implementadas](#-características-implementadas)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Uso](#-uso)
- [Documentación](#-documentación)
- [Testing](#-testing)
- [Despliegue](#-despliegue)
- [Estado del Proyecto](#-estado-del-proyecto)
- [Licencia y Uso](#-licencia-y-uso)
- [Autor](#-autor)

---

## 🎯 Sobre Este Proyecto

**YouTube AI Summary** es un sistema de agregación inteligente de contenido que **automáticamente extrae, transcribe y resume vídeos de YouTube** relacionados con IA, desarrollo y tecnología. El sistema genera resúmenes personalizados y los distribuye a través de un bot de Telegram multi-usuario.

### ¿Por Qué Está "Overengineered"?

Este proyecto **NO** es la forma más simple de resolver el problema. Una solución práctica requeriría ~500 líneas de código en un solo script. Sin embargo, este proyecto implementa:

- ✅ **Clean Architecture** con separación de capas
- ✅ **API REST profesional** con FastAPI, OpenAPI y Swagger
- ✅ **CI/CD completo** con GitHub Actions
- ✅ **Monitorización** con Prometheus y Grafana
- ✅ **Testing exhaustivo** (177+ tests, >80% coverage)
- ✅ **Seguridad** (JWT, rate limiting, prompt injection prevention)
- ✅ **Containerización** con Docker y Docker Compose
- ✅ **ORM** con SQLAlchemy 2.0 y PostgreSQL
- ✅ **Cache distribuida** con Redis
- ✅ **Cola de tareas** asíncrona con Celery
- ✅ **Logs estructurados** en JSON con contexto
- ✅ **Métricas** exportadas a Prometheus
- ✅ **Documentación técnica** exhaustiva (22,500+ líneas)

**Este overengineering es deliberado y educativo.** El objetivo es practicar y demostrar competencias profesionales en desarrollo backend moderno.

---

## 📚 Objetivos de Aprendizaje

Este proyecto fue diseñado específicamente para aprender y practicar:

### 🏗️ Arquitectura y Diseño

- **Clean Architecture**: Separación estricta de capas (API, servicios, repositorios, modelos)
- **Arquitectura Modular Monolítica**: Organización escalable sin microservicios prematuros
- **Patrones de Diseño**: Repository pattern, dependency injection, factory pattern
- **ADRs (Architecture Decision Records)**: Documentación de decisiones arquitectónicas

### 🚀 Desarrollo Backend Profesional

- **FastAPI**: Framework asíncrono moderno para APIs REST
- **OpenAPI/Swagger**: Documentación automática e interactiva de la API
- **ReDoc**: Documentación alternativa generada automáticamente
- **Pydantic**: Validación de datos con type hints
- **SQLAlchemy 2.0**: ORM con soporte asíncrono y migrations con Alembic
- **PostgreSQL**: Base de datos relacional con JSONB, full-text search, índices GIN
- **Redis**: Cache distribuida y backend para Celery
- **Celery + Beat**: Cola de tareas asíncrona con scheduling

### 🐳 DevOps y Containerización

- **Docker**: Containerización de aplicaciones
- **Docker Compose**: Orquestación local de infraestructura (PostgreSQL, Redis, Grafana, Prometheus)
- **Multi-stage builds**: Optimización de imágenes Docker
- **Health checks**: Validación de servicios en contenedores
- **Volumes**: Persistencia de datos

### 🔄 CI/CD y Automatización

- **GitHub Actions**: Pipelines automáticos de integración y despliegue
- **Test Automation**: Ejecución automática de 177+ tests
- **Coverage Gates**: Validación de cobertura mínima (>80%)
- **Linting Automation**: Black, Ruff, mypy en CI
- **Security Scanning**: Tests de seguridad automatizados

### 🧪 Testing y Calidad de Código

- **pytest**: Framework de testing moderno
- **pytest-asyncio**: Tests para código asíncrono
- **pytest-cov**: Reportes de cobertura (HTML, XML, terminal)
- **Tests Unitarios**: Lógica de negocio aislada
- **Tests de Integración**: Interacción entre componentes
- **Tests de Seguridad**: JWT, rate limiting, validación
- **Tests E2E**: Flujos completos de usuario
- **Coverage >80%**: Métricas de calidad cuantificables

### 🔒 Seguridad

- **JWT Authentication**: Tokens seguros con refresh tokens
- **Role-Based Access Control**: Admin vs usuario normal
- **Rate Limiting**: Protección contra brute-force (SlowAPI + Redis)
- **Input Validation**: Sanitización de entradas con Pydantic
- **Prompt Injection Prevention**: Mitigación de ataques a LLMs
- **Output Validation**: Verificación de respuestas de IA
- **bcrypt**: Hashing seguro de contraseñas
- **CORS**: Configuración de orígenes permitidos

### 📊 Observabilidad y Monitorización

- **Prometheus**: Métricas de aplicación (counters, histograms, gauges)
- **Grafana**: Dashboards visuales en tiempo real
- **Structured Logging**: Logs en JSON con contexto (structlog)
- **Request ID Middleware**: Trazabilidad de peticiones
- **Health Checks**: Endpoints de salud para monitoreo
- **Alerting**: Configuración de alertas automáticas

### 🤖 Integración de IA

- **Whisper (OpenAI)**: Transcripción local de audio (modelo base, 85-90% accuracy)
- **DeepSeek API**: Generación de resúmenes con LLM ($0.28/1M tokens)
- **Context Caching**: Optimización de costes con DeepSeek
- **Prompt Engineering**: Diseño de prompts estructurados para JSON
- **Output Validation**: Verificación de respuestas del modelo

### 🤝 Trabajo con IA Asistida

- **Claude Code**: Desarrollo asistido con supervisión humana
- **Prompts Inteligentes**: Sistema de roles especializados para Claude
- **Modo Agente**: Automatización supervisada de tareas complejas
- **Documentación IA-Generada**: ADRs, guías técnicas, análisis de código
- **Code Review Asistido**: Detección de problemas con IA

### 🔧 Gestión de Proyecto

- **Git**: Control de versiones con commits semánticos
- **GitHub**: Hosting, issues, PRs, projects
- **Conventional Commits**: Mensajes estructurados (feat, fix, docs, refactor, test)
- **Branching Strategy**: Feature branches con merges a main
- **Pull Requests**: Revisión de código y CI checks

### 🌐 Despliegue en Servidor Real

- **Linux (Ubuntu 24.04)**: Administración de servidor
- **Systemd Services**: Servicios gestionados por systemd
- **Cloudflare Tunnel**: Exposición segura sin IP pública
- **Nginx**: Reverse proxy (opcional)
- **Environment Management**: Variables de entorno con .env
- **Log Rotation**: Gestión de logs en producción

### 📖 Buenas Prácticas de Código

- **PEP 8**: Estilo de código Python estándar
- **Type Hints**: Tipado estático en Python
- **Docstrings**: Documentación en el código
- **Black**: Formateo automático consistente
- **Ruff**: Linter rápido con reglas modernas
- **mypy**: Verificación de tipos estática
- **Clean Code**: Funciones cortas, nombres descriptivos, SRP

---

## 🛠️ Tecnologías y Herramientas

### Backend Core

| Tecnología   | Versión | Propósito               |
| ------------ | ------- | ----------------------- |
| **Python**   | 3.11+   | Lenguaje principal      |
| **FastAPI**  | 0.115+  | Framework web asíncrono |
| **Uvicorn**  | 0.32+   | Servidor ASGI           |
| **Pydantic** | 2.10+   | Validación de datos     |

### Base de Datos y Persistencia

| Tecnología          | Versión | Propósito                |
| ------------------- | ------- | ------------------------ |
| **PostgreSQL**      | 15      | Base de datos relacional |
| **SQLAlchemy**      | 2.0.36+ | ORM con async            |
| **Alembic**         | 1.14+   | Migraciones de BD        |
| **psycopg2-binary** | 2.9+    | Driver PostgreSQL        |

### Cache y Cola de Tareas

| Tecnología      | Versión  | Propósito                  |
| --------------- | -------- | -------------------------- |
| **Redis**       | 7        | Cache + broker Celery      |
| **Celery**      | 5.4+     | Cola de tareas distribuida |
| **Celery Beat** | Incluido | Scheduler de tareas        |

### IA y Machine Learning

| Tecnología       | Versión        | Propósito               |
| ---------------- | -------------- | ----------------------- |
| **Whisper**      | 20240930       | Transcripción de audio  |
| **DeepSeek API** | Via OpenAI SDK | Generación de resúmenes |
| **yt-dlp**       | 2024.12+       | Descarga de YouTube     |

### Monitorización y Observabilidad

| Tecnología            | Versión | Propósito               |
| --------------------- | ------- | ----------------------- |
| **Prometheus**        | -       | Recolección de métricas |
| **Grafana**           | -       | Dashboards visuales     |
| **structlog**         | 24.4+   | Logging estructurado    |
| **prometheus_client** | 0.21+   | Exportación de métricas |

### Seguridad

| Tecnología      | Versión | Propósito            |
| --------------- | ------- | -------------------- |
| **python-jose** | 3.5+    | JWT tokens           |
| **bcrypt**      | 5.0+    | Hashing de passwords |
| **slowapi**     | 0.1.9+  | Rate limiting        |

### Bot de Telegram

| Tecnología              | Versión | Propósito               |
| ----------------------- | ------- | ----------------------- |
| **python-telegram-bot** | 22.5+   | SDK oficial de Telegram |

### DevOps y CI/CD

| Tecnología         | Propósito               |
| ------------------ | ----------------------- |
| **Docker**         | Containerización        |
| **Docker Compose** | Orquestación local      |
| **GitHub Actions** | CI/CD automation        |
| **Poetry**         | Gestión de dependencias |

### Testing y Calidad

| Herramienta        | Propósito           |
| ------------------ | ------------------- |
| **pytest**         | Framework de tests  |
| **pytest-asyncio** | Tests asíncronos    |
| **pytest-cov**     | Cobertura de código |
| **Black**          | Formateo automático |
| **Ruff**           | Linting moderno     |
| **mypy**           | Type checking       |

---

## 🏛️ Arquitectura

### Clean Architecture - Separación de Capas

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                  │
│  - Routes (videos, summaries, transcriptions, stats)    │
│  - Schemas (Pydantic models)                           │
│  - Dependencies (auth, db sessions)                     │
│  - Middleware (request ID, CORS, rate limiting)        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Service Layer (Business Logic)             │
│  - VideoProcessingService                              │
│  - TranscriptionService (Whisper)                      │
│  - SummarizationService (DeepSeek)                     │
│  - YoutubescraperService                               │
│  - CacheService (Redis)                                │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│          Repository Layer (Data Access)                 │
│  - VideoRepository                                      │
│  - SummaryRepository                                    │
│  - TranscriptionRepository                             │
│  - UserRepository                                       │
│  - BaseRepository (CRUD genérico)                      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Model Layer (SQLAlchemy ORM)               │
│  - Video, Summary, Transcription                       │
│  - Source (channels), TelegramUser                     │
│  - User (API auth)                                     │
└─────────────────────────────────────────────────────────┘
```

### Estructura de Directorios

```
youtube-AIsummary/
├── src/
│   ├── api/              # Capa de presentación FastAPI
│   │   ├── auth/         # Autenticación JWT
│   │   ├── routes/       # Endpoints REST
│   │   ├── schemas/      # Modelos Pydantic
│   │   ├── middleware/   # Request ID, CORS
│   │   └── dependencies.py
│   ├── bot/              # Bot de Telegram multi-usuario
│   │   ├── handlers/     # Comandos (/start, /help, /search)
│   │   └── telegram_bot.py
│   ├── core/             # Infraestructura
│   │   ├── config.py     # Settings con Pydantic
│   │   ├── database.py   # SQLAlchemy setup
│   │   ├── celery_app.py # Celery config
│   │   ├── logging_config.py  # Structured logging
│   │   ├── metrics.py    # Prometheus metrics
│   │   └── security.py   # Password hashing
│   ├── models/           # ORM SQLAlchemy
│   │   ├── video.py
│   │   ├── summary.py
│   │   ├── transcription.py
│   │   ├── source.py
│   │   ├── telegram_user.py
│   │   └── user.py
│   ├── repositories/     # Acceso a datos
│   │   ├── base_repository.py
│   │   └── *_repository.py
│   ├── services/         # Lógica de negocio
│   │   ├── video_processing_service.py
│   │   ├── transcription_service.py
│   │   ├── summarization_service.py
│   │   ├── youtube_scraper_service.py
│   │   ├── downloader_service.py
│   │   ├── cache_service.py
│   │   ├── input_sanitizer.py
│   │   └── output_validator.py
│   ├── tasks/            # Celery workers
│   │   ├── video_processing.py
│   │   ├── scraping.py
│   │   └── distribute_summaries.py
│   └── utils/
├── tests/
│   ├── unit/             # Tests unitarios
│   ├── integration/      # Tests de integración
│   ├── security/         # Tests de seguridad
│   ├── api/              # Tests de endpoints
│   └── e2e/              # Tests end-to-end
├── docs/
│   ├── architecture.md   # Arquitectura completa + ADRs
│   ├── roadmap.md        # Plan de desarrollo (25+ pasos)
│   ├── security-audit-report.md
│   ├── prometheus-guide.md
│   ├── grafana-dashboards-guide.md
│   └── contexting-prompts/  # Prompts para Claude Code
├── alembic/
│   └── versions/         # Migraciones de BD
├── .github/
│   └── workflows/        # CI/CD pipelines
├── docker-compose.yml    # Infraestructura local
├── Dockerfile            # Imagen de producción
├── pyproject.toml        # Poetry config + tools
├── prometheus.yml        # Config Prometheus
└── .env.example          # Template de variables
```

---

## ⚡ Características Implementadas

### 🎥 Pipeline Completo de Procesamiento

- **Scraping Automático**: Descubrimiento periódico de vídeos nuevos (Celery Beat)
- **Descarga de Audio**: Extracción eficiente con yt-dlp
- **Transcripción Local**: Whisper modelo base (85-90% accuracy, sin costes API)
- **Resumen con IA**: DeepSeek API ($0.28/1M tokens, context caching)
- **Distribución Personalizada**: Telegram bot con suscripciones por usuario
- **Estados Tracked**: 9 estados diferentes (pending → completed/failed/skipped)

### 🌐 API REST Profesional

- **OpenAPI/Swagger**: Documentación interactiva en `/docs`
- **ReDoc**: Documentación alternativa en `/redoc`
- **CRUD Completo**: Videos, summaries, transcriptions
- **Full-Text Search**: Búsqueda en español con GIN indexes
- **Cursor Pagination**: Eficiente para datasets grandes
- **Rate Limiting**: Protección contra abuso (configurable por endpoint)
- **JWT Authentication**: Tokens de acceso + refresh (role-based)
- **Health Checks**: `/health` y `/metrics` para monitoreo

### 🤖 Bot de Telegram Multi-Usuario

**Comandos Interactivos:**
- `/start` - Registro de usuario nuevo
- `/help` - Lista de comandos disponibles
- `/sources` - Ver canales disponibles (con botones de suscripción)
- `/recent` - Últimos resúmenes (personalizados)
- `/search <query>` - Búsqueda full-text en resúmenes
- `/history` - Historial de interacciones

**Características:**
- Teclados inline para suscripciones
- Callback handlers para botones
- Formateo markdown + emojis
- Detección de bloqueo del bot
- Suscripciones independientes por usuario

---

## 📥 Instalación y Configuración

### Prerrequisitos

- **Python 3.11+** ([Descargar](https://www.python.org/downloads/))
- **Poetry** ([Instalar](https://python-poetry.org/docs/#installation))
- **Docker** y **Docker Compose** ([Instalar](https://docs.docker.com/get-docker/))
- **Git** ([Descargar](https://git-scm.com/downloads))

### Instalación Rápida

```bash
# 1. Clonar repositorio
git clone https://github.com/Prodelaya/youtube-AIsummary.git
cd youtube-AIsummary

# 2. Instalar dependencias
poetry install

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 4. Levantar infraestructura
docker-compose up -d

# 5. Ejecutar migraciones
poetry run alembic upgrade head

# 6. Levantar la aplicación
poetry run uvicorn src.api.main:app --reload
```

**Guía completa de instalación:** Ver sección completa en el README original o [`docs/installation-guide.md`](docs/installation-guide.md)

---

## 📖 Documentación

Este proyecto incluye **documentación técnica exhaustiva** (>22,500 líneas):

### Documentación Principal

| Documento                                                              | Descripción                              |
| ---------------------------------------------------------------------- | ---------------------------------------- |
| [`docs/architecture.md`](docs/architecture.md)                         | Arquitectura completa del sistema + ADRs |
| [`docs/roadmap.md`](docs/roadmap.md)                                   | Plan de desarrollo en 30+ pasos          |
| [`docs/security-audit-report.md`](docs/security-audit-report.md)       | Análisis de seguridad exhaustivo         |
| [`docs/prometheus-guide.md`](docs/prometheus-guide.md)                 | Setup, queries, alerting                 |
| [`docs/grafana-dashboards-guide.md`](docs/grafana-dashboards-guide.md) | Dashboards y visualización               |

### Prompts para Claude Code

Este proyecto utiliza **prompts especializados** para desarrollo asistido con Claude Code:

| Prompt                                                                             | Rol                        |
| ---------------------------------------------------------------------------------- | -------------------------- |
| [`1-project-designer.md`](docs/contexting-prompts/1-project-designer.md)           | Arquitecto de software     |
| [`2-incremental-builder.md`](docs/contexting-prompts/2-incremental-builder.md)     | Desarrollador incremental  |
| [`3-code-review--refactor.md`](docs/contexting-prompts/3-code-review--refactor.md) | Revisor/Refactorizador     |
| [`4-diagnostic-expert.md`](docs/contexting-prompts/4-diagnostic-expert.md)         | Diagnóstico y optimización |
| [`5-deployment--ops.md`](docs/contexting-prompts/5-deployment--ops.md)             | DevOps/Mantenimiento       |
| [`6-documentation-mentor.md`](docs/contexting-prompts/6-documentation-mentor.md)   | Documentación técnica      |

---

## 🧪 Testing

```bash
# Todos los tests
poetry run pytest

# Con coverage report
poetry run pytest --cov=src --cov-report=html

# Solo tests de seguridad
poetry run pytest tests/security

# Ver reporte HTML
xdg-open htmlcov/index.html
```

**Coverage Actual:** >80% (177+ tests)

---

## 📊 Estado del Proyecto

### ✅ Completado (Step 25 - CI/CD)

- ✅ Infraestructura completa (PostgreSQL, Redis, Docker)
- ✅ API REST con FastAPI + OpenAPI
- ✅ Pipeline de procesamiento de vídeos
- ✅ Transcripción con Whisper
- ✅ Resúmenes con DeepSeek API
- ✅ Bot de Telegram multi-usuario
- ✅ Sistema de cache con Redis
- ✅ Autenticación JWT + RBAC
- ✅ Rate limiting + Security
- ✅ Monitorización (Prometheus + Grafana)
- ✅ Testing exhaustivo (177+ tests, >80% coverage)
- ✅ CI/CD con GitHub Actions
- ✅ Documentación técnica completa

### Métricas del Proyecto

| Métrica                     | Valor    |
| --------------------------- | -------- |
| **Líneas de Código (src/)** | ~15,000+ |
| **Líneas de Tests**         | ~8,000+  |
| **Líneas de Documentación** | ~22,500+ |
| **Tests Totales**           | 177+     |
| **Coverage**                | >80%     |
| **Commits**                 | 150+     |

---

## 📜 Licencia y Uso

### Licencia MIT

**Eres libre de:**
- ✅ Usar el código para tus propios proyectos
- ✅ Modificarlo según tus necesidades
- ✅ Distribuirlo y usarlo comercialmente
- ✅ Ofrecer servicios basados en este código

**Con la condición de:**
- ⚠️ **Mencionar la autoría original** (Pablo - @prodelaya)
- ⚠️ Incluir una copia de la licencia MIT

### Uso del Proyecto

**Este proyecto puede usarse para:**
- Aprender Clean Architecture y desarrollo backend moderno
- Practicar CI/CD, Docker, testing, seguridad
- Agregador personal de resúmenes de YouTube
- Servicio para terceros (con atribución)
- Portafolio profesional

**Modelos de IA:**
- Por defecto: **DeepSeek** ($0.28/1M tokens)
- Compatible con: OpenAI GPT, Claude, Llama, Mistral, cualquier LLM compatible con OpenAI SDK

---

## 🤝 Contribuciones y Feedback

**Toda opinión crítica constructiva y/o sugerencia es bienvenida.**

Si encuentras bugs, mejoras, o tienes sugerencias:
- 🐛 [Abrir un Issue](https://github.com/Prodelaya/youtube-AIsummary/issues)
- 💬 [Discusiones](https://github.com/Prodelaya/youtube-AIsummary/discussions)

---

## 👨‍💻 Autor

**Pablo** (@prodelaya)

- GitHub: [@Prodelaya](https://github.com/Prodelaya)

### Agradecimientos

- **Claude Code (Anthropic)**: Asistente de desarrollo con modo agente
- **OpenAI**: Whisper para transcripción local
- **DeepSeek**: API económica y eficiente para resúmenes
- **FastAPI Team**: Framework increíble
- **Python Community**: Ecosistema de calidad

---

## 📝 Notas Finales

### ¿Por Qué "Overengineered"?

Este proyecto **deliberadamente** implementa soluciones de nivel empresarial para un problema simple. **El objetivo es educativo:**

1. **Aprendizaje Completo**: Practicar tecnologías de producción real
2. **Portafolio Profesional**: Demostrar capacidades técnicas
3. **Referencia Futura**: Base de conocimiento consultable
4. **Experimentación**: Probar herramientas en entorno controlado
5. **Documentación**: Crear guías útiles para la comunidad

### ¿Cuándo Usar Este Proyecto?

**✅ USA este proyecto si:**
- Estás aprendiendo desarrollo backend moderno
- Quieres entender Clean Architecture en práctica
- Necesitas ejemplo de CI/CD completo
- Buscas implementar observabilidad
- Quieres portafolio de calidad

**❌ NO uses este proyecto si:**
- Solo quieres resumir vídeos (usa un script simple de ~100 líneas)
- No tienes tiempo para setup complejo
- Prefieres soluciones minimalistas

---

<div align="center">

**Proyecto Didáctico de Arquitectura Backend Profesional**

Creado con ❤️ por [@Prodelaya](https://github.com/Prodelaya)

**Última Actualización:** Noviembre 2025 | **Versión:** 0.1.0

*"Lo perfecto es enemigo de lo bueno, pero lo overengineered es amigo del aprendizaje."*

**⭐ Si te ha sido útil, dale una estrella al repositorio**

</div>
