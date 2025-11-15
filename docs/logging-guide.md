# Guía de Logging Estructurado

## 📋 Índice

1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Uso Básico](#uso-básico)
4. [Context Managers](#context-managers)
5. [Convenciones de Nombres](#convenciones-de-nombres)
6. [Ejemplos por Componente](#ejemplos-por-componente)
7. [Queries Útiles](#queries-útiles)
8. [Troubleshooting](#troubleshooting)

---

## Introducción

Este proyecto utiliza **logging estructurado** con [structlog](https://www.structlog.org/) para proporcionar:

- ✅ **Formato JSON consistente** - Todos los logs son parseables automáticamente
- ✅ **Request ID** - Correlación automática entre operaciones relacionadas
- ✅ **Contexto enriquecido** - Información estructurada que permite queries complejas
- ✅ **Filtrado automático** - Tokens/passwords nunca aparecen en logs
- ✅ **Rotación automática** - Archivos de log rotan al alcanzar 100MB

---

## Arquitectura del Sistema

### Componentes Principales

```
src/core/logging_config.py
├── get_logger(module_name)          # Factory de loggers
├── configure_logging(env, component) # Configuración base
└── Processors
    ├── add_app_context()             # Añade contexto de aplicación
    ├── filter_sensitive_data()       # Filtra tokens/passwords
    └── add_request_id()              # Request ID (contextvars)

src/api/middleware/request_id.py     # Middleware FastAPI
src/core/celery_context.py           # Context manager Celery
src/bot/context_manager.py           # Context manager Bot
```

### Archivos de Log

| Archivo | Componente | Descripción |
|---------|-----------|-------------|
| `logs/app.json` | FastAPI + Servicios | Logs de API y servicios de negocio |
| `logs/celery.json` | Workers Celery | Logs de tasks asíncronas |
| `logs/bot.json` | Bot Telegram | Logs de handlers del bot |

---

## Uso Básico

### 1. Importar el Logger

```python
from src.core.logging_config import get_logger

logger = get_logger(__name__)
```

⚠️ **IMPORTANTE**: Nunca uses `logging.getLogger()`, siempre usa `get_logger()`.

### 2. Logging Simple

```python
# ❌ INCORRECTO - No estructurado
logger.info(f"Processing video {video_id}")

# ✅ CORRECTO - Estructurado
logger.bind(video_id=str(video_id)).info("video_processing_started")
```

### 3. Logging con Múltiples Campos

```python
logger.bind(
    video_id=str(video.id),
    youtube_id=video.youtube_id,
    duration_seconds=video.duration_seconds,
    status=video.status.value,
).info("video_downloaded")
```

**Output JSON:**
```json
{
  "timestamp": "2025-11-15T14:30:45.123Z",
  "level": "info",
  "event": "video_downloaded",
  "module": "src.services.video_processing_service",
  "request_id": "req-7f8a9b0c",
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "youtube_id": "dQw4w9WgXcQ",
  "duration_seconds": 1245,
  "status": "downloaded"
}
```

---

## Context Managers

### FastAPI (Automático)

El middleware `RequestIDMiddleware` inyecta automáticamente el Request ID en todos los logs de requests HTTP.

**No necesitas hacer nada** - el middleware se encarga de todo.

### Celery Tasks

Usa el context manager `task_context()` para añadir contexto automático:

```python
from src.core.celery_context import task_context

@celery_app.task
def process_video_task(video_id: str):
    with task_context(
        task_name="process_video",
        video_id=video_id,
    ):
        # Todos los logs aquí tendrán request_id, task_name y video_id
        logger.info("processing_started")

        # Añadir contexto progresivamente
        from src.core.celery_context import bind_task_context
        bind_task_context(youtube_id="dQw4w9WgXcQ")

        logger.info("video_downloaded")
        # Este log incluirá: request_id, task_name, video_id, youtube_id
```

### Bot de Telegram

Usa el context manager `bot_update_context()`:

```python
from src.bot.context_manager import bot_update_context

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_update_context(update, command="start"):
        # Todos los logs incluirán: request_id (update_id), user_id, chat_id, command
        logger.info("user_started_bot")
```

---

## Convenciones de Nombres

### Eventos (event)

Los nombres de eventos deben ser:

- ✅ **snake_case** (minúsculas con guiones bajos)
- ✅ **Descriptivos** (verbo + objeto + contexto)
- ✅ **Sin f-strings** (datos estructurados en `.bind()`)

**Ejemplos correctos:**

```python
# Operaciones normales
logger.info("video_processing_started")
logger.info("audio_downloaded")
logger.info("transcription_completed")
logger.info("summary_created")

# Operaciones completadas
logger.info("distribution_completed")
logger.info("scraping_finished")

# Advertencias
logger.warning("video_skipped_duration_exceeded")
logger.warning("user_blocked_bot")

# Errores
logger.error("video_processing_failed_download")
logger.error("telegram_send_failed")
```

**Ejemplos incorrectos:**

```python
# ❌ CamelCase
logger.info("VideoProcessingStarted")

# ❌ F-strings en evento
logger.info(f"Processing video {video_id}")

# ❌ Demasiado genérico
logger.info("started")
logger.info("error")
```

### Campos de Contexto

| Campo | Tipo | Uso |
|-------|------|-----|
| `video_id` | UUID (string) | Identificador de video |
| `summary_id` | UUID (string) | Identificador de resumen |
| `user_id` | UUID (string) | Identificador de usuario BD |
| `telegram_user_id` | int | Telegram chat ID |
| `youtube_id` | string | ID de YouTube (ej: "dQw4w9WgXcQ") |
| `source_id` | UUID (string) | Identificador de source |
| `duration_seconds` | int | Duración en segundos |
| `error` | string | Mensaje de error |
| `error_type` | string | Clase de excepción |
| `status` | string | Estado (ej: "downloading", "completed") |

---

## Ejemplos por Componente

### VideoProcessingService

```python
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class VideoProcessingService:
    async def process_video(self, session: Session, video_id: UUID) -> Video:
        logger.bind(
            video_id=str(video_id),
            youtube_id=video.youtube_id,
        ).info("video_processing_started")

        try:
            # Procesar video...
            logger.bind(
                video_id=str(video.id),
                transcription_id=str(transcription.id),
            ).info("video_processing_completed")

        except TranscriptionFailedError as e:
            logger.bind(
                video_id=str(video.id),
                error=str(e),
            ).error("video_processing_failed_transcription")
            raise
```

### Celery Task

```python
from src.core.celery_context import task_context
from src.core.logging_config import get_logger

logger = get_logger(__name__)

@celery_app.task
def distribute_summary_task(self, summary_id_str: str):
    with task_context(
        task_name="distribute_summary",
        summary_id=summary_id_str,
    ):
        logger.bind(
            total_subscribers=len(subscribed_users),
            active_users=len(active_users),
        ).info("users_count_calculated")

        # Distribuir...

        logger.bind(
            messages_sent=len(sent_message_ids),
        ).info("distribution_completed")
```

### Bot de Telegram

```python
from src.bot.context_manager import bot_update_context
from src.core.logging_config import get_logger

logger = get_logger(__name__)

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_update_context(update, command="search"):
        query = update.message.text

        logger.bind(search_query=query).info("search_executed")

        # Buscar...

        logger.bind(results_count=len(results)).info("search_completed")
```

---

## Queries Útiles

### Ver logs en tiempo real

```bash
tail -f logs/app.json | jq .
```

### Buscar por Request ID

```bash
grep "req-abc123" logs/*.json | jq .
```

### Contar errores por módulo

```bash
cat logs/app.json | jq -r 'select(.level=="error") | .module' | sort | uniq -c
```

### Ver latencias de operaciones

```bash
cat logs/app.json | jq 'select(.duration_ms) | {event, duration_ms}' | jq -s 'sort_by(.duration_ms) | reverse | .[0:10]'
```

### Filtrar eventos específicos

```bash
cat logs/app.json | jq 'select(.event=="video_processing_started")'
```

### Ver todos los logs de un video específico

```bash
cat logs/app.json | jq 'select(.video_id=="550e8400-e29b-41d4-a716-446655440000")'
```

### Trazabilidad end-to-end por Request ID

```bash
# Obtener todos los logs relacionados con un request
cat logs/*.json | jq 'select(.request_id=="req-abc123")' | jq -s 'sort_by(.timestamp)'
```

---

## Troubleshooting

### Logs no aparecen en archivo

**Problema:** Logs no se escriben en `logs/app.json`

**Solución:**
1. Verificar que el directorio `logs/` existe
2. Verificar permisos de escritura
3. Verificar que `logging_config.py` se importó correctamente

### Logs sin Request ID

**Problema:** Logs no incluyen `request_id`

**Solución:**
- **FastAPI:** Verificar que `RequestIDMiddleware` está añadido
- **Celery:** Verificar que usas `task_context()`
- **Bot:** Verificar que usas `bot_update_context()`

### Tokens aparecen en logs

**Problema:** Tokens/passwords visibles en logs

**Solución:**
El filtro automático debería encargarse de esto. Si no funciona:
1. Verificar que el campo está en `SENSITIVE_FIELDS` en `logging_config.py`
2. Añadir el campo si es necesario

### Archivo de log demasiado grande

**Problema:** `app.json` crece sin control

**Solución:**
La rotación automática está configurada (100MB, 10 backups). Si no funciona:
1. Verificar configuración de `RotatingFileHandler` en `logging_config.py`
2. Ejecutar script de cleanup manualmente

### Performance degradada

**Problema:** Logging causa lentitud

**Solución:**
1. Reducir nivel de logging (INFO → WARNING en producción)
2. Verificar que no hay logging en loops muy frecuentes
3. Usar logging asíncrono si es necesario

---

## Referencias

- [Documentación structlog](https://www.structlog.org/en/stable/)
- [Convenciones de commits](./commit-guide.md)
- [Clean Code Guide](./clean-code.md)
- [Architecture](./architecture.md)

---

**Última actualización:** 15 de noviembre de 2025
**Mantenedor:** Pablo (prodelaya)
