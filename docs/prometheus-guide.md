# Guía de Desarrollo: Sistema de Métricas Prometheus

**Proyecto:** youtube-AIsummary
**Paso:** 22 - Sistema de Métricas
**Última actualización:** 15/11/2025

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Módulo Centralizado de Métricas](#módulo-centralizado-de-métricas)
4. [Tipos de Métricas](#tipos-de-métricas)
5. [Categorías de Métricas](#categorías-de-métricas)
6. [Cómo Añadir Nuevas Métricas](#cómo-añadir-nuevas-métricas)
7. [Mejores Prácticas](#mejores-prácticas)
8. [Troubleshooting](#troubleshooting)

---

## Introducción

Este proyecto implementa un sistema de **observabilidad** basado en Prometheus para monitorizar:

- Rendimiento de la API (FastAPI)
- Procesamiento de videos (pipeline completo)
- Tareas asíncronas (Celery)
- Cache (Redis)
- Base de datos (PostgreSQL)
- Sistema operativo (CPU, RAM, disco)

### Beneficios

✅ **Monitorización en tiempo real** de todos los componentes
✅ **Detección temprana** de cuellos de botella y errores
✅ **Análisis histórico** con retención de 15 días
✅ **Alerting** (futuro) basado en métricas críticas
✅ **Dashboards** visuales en Grafana

---

## Arquitectura del Sistema

```
┌─────────────────┐
│   FastAPI App   │
│  (Puerto 8000)  │
│                 │
│  /metrics       │◄─────┐
│  (texto plano)  │      │
└─────────────────┘      │
                         │ Scrape cada 15s
┌─────────────────┐      │
│  Prometheus     │──────┘
│  (Puerto 9090)  │
│                 │
│  TSDB (15 días) │
└─────────────────┘
         │
         │ Queries (PromQL)
         ▼
┌─────────────────┐
│    Grafana      │
│  (Puerto 3000)  │
│                 │
│   Dashboards    │
└─────────────────┘
```

### Flujo de Datos

1. **Aplicación** genera métricas usando `src/core/metrics.py`
2. **Prometheus** hace scraping de `/metrics` cada 15 segundos
3. **TSDB** almacena series temporales con retención de 15 días
4. **Grafana** consulta Prometheus con PromQL y muestra dashboards

---

## Módulo Centralizado de Métricas

**Ubicación:** `src/core/metrics.py`

### ¿Por Qué Centralizado?

❌ **Antes (Descentralizado):**
```python
# En cache_service.py
cache_hits = Counter("cache_hits_total", ...)

# En video_service.py
cache_hits = Counter("cache_hits_total", ...)  # ⚠️ DUPLICADO!
```

**Error:** `ValueError: Duplicated timeseries in CollectorRegistry`

✅ **Ahora (Centralizado):**
```python
# src/core/metrics.py
class PrometheusMetrics:
    def __init__(self):
        self.cache_hits_total = Counter("cache_hits_total", ...)

# En cualquier módulo
from src.core.metrics import metrics
metrics.cache_hits_total.labels(cache_type="summary").inc()
```

### Patrón Singleton

El módulo usa **Singleton** para garantizar una única instancia global:

```python
class PrometheusMetrics:
    _instance: Optional['PrometheusMetrics'] = None

    def __new__(cls, registry: Optional[CollectorRegistry] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        if self._initialized:
            return

        self._registry = registry or REGISTRY
        self._init_http_metrics()
        self._init_video_metrics()
        # ...
        self._initialized = True

# Instancia global
metrics = PrometheusMetrics()
```

**Ventajas:**
- ✅ Una única definición de cada métrica
- ✅ Compartida por toda la aplicación
- ✅ Testeable con registros customizados

---

## Tipos de Métricas

Prometheus soporta 4 tipos de métricas. Cada una tiene un propósito específico.

### 1. Counter (Contador)

**Definición:** Valor que **solo puede incrementar** (nunca decrece).

**Cuándo usar:**
- Número total de requests HTTP
- Número total de videos procesados
- Número total de errores

**Ejemplo:**
```python
# Definición
self.http_requests_total = Counter(
    'http_requests_total',
    'Total de requests HTTP recibidos',
    ['method', 'endpoint', 'status'],
    registry=self._registry
)

# Uso
metrics.http_requests_total.labels(
    method="GET",
    endpoint="/api/videos",
    status="200"
).inc()  # Incrementa en 1

metrics.http_requests_total.labels(
    method="POST",
    endpoint="/api/videos",
    status="201"
).inc(5)  # Incrementa en 5
```

**Convenciones de nombres:**
- ✅ Termina en `_total`: `http_requests_total`
- ✅ Usa plural: `errors_total`, `requests_total`

### 2. Gauge (Indicador)

**Definición:** Valor que puede **subir y bajar**.

**Cuándo usar:**
- CPU usage (%)
- Memoria RAM usada
- Tareas Celery en cola
- Conexiones activas

**Ejemplo:**
```python
# Definición
self.celery_queue_size = Gauge(
    'celery_queue_size',
    'Número de tareas pendientes en cola Celery',
    ['queue_name'],
    registry=self._registry
)

# Uso
metrics.celery_queue_size.labels(queue_name="video_processing").set(42)
metrics.celery_queue_size.labels(queue_name="video_processing").inc()   # +1
metrics.celery_queue_size.labels(queue_name="video_processing").dec(5)  # -5
```

**Convenciones de nombres:**
- ✅ Sin sufijo especial: `celery_queue_size`, `memory_usage_bytes`
- ✅ Usa unidades claras: `_bytes`, `_percent`

### 3. Histogram (Histograma)

**Definición:** Distribuye observaciones en **buckets predefinidos**.

**Cuándo usar:**
- Latencias de requests HTTP
- Tiempos de procesamiento
- Tamaños de archivos

**Ejemplo:**
```python
# Definición
self.http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'Duración de requests HTTP',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=self._registry
)

# Uso
import time
start = time.time()
# ... procesar request ...
duration = time.time() - start
metrics.http_request_duration_seconds.labels(
    method="GET",
    endpoint="/api/videos"
).observe(duration)
```

**Métricas generadas automáticamente:**
```
http_request_duration_seconds_bucket{le="0.005"} 150
http_request_duration_seconds_bucket{le="0.01"} 200
http_request_duration_seconds_bucket{le="+Inf"} 250
http_request_duration_seconds_sum 12.34
http_request_duration_seconds_count 250
```

**Queries útiles:**
```promql
# Percentil 95 de latencia
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Latencia promedio
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

**Convenciones de nombres:**
- ✅ Termina en unidad de medida: `_seconds`, `_bytes`

### 4. Summary (Resumen)

**Definición:** Similar a Histogram pero calcula **cuantiles en el cliente**.

**Cuándo usar:**
- Cuando necesitas cuantiles precisos (p50, p90, p99)
- Cuando no conoces el rango de valores de antemano

**Ejemplo:**
```python
# Definición
self.cache_operation_duration_seconds = Summary(
    'cache_operation_duration_seconds',
    'Duración de operaciones de cache',
    ['operation'],
    registry=self._registry
)

# Uso
import time
start = time.time()
# ... operación de cache ...
duration = time.time() - start
metrics.cache_operation_duration_seconds.labels(
    operation="get"
).observe(duration)
```

**Métricas generadas automáticamente:**
```
cache_operation_duration_seconds_sum{operation="get"} 45.67
cache_operation_duration_seconds_count{operation="get"} 1000
```

**Diferencias Histogram vs Summary:**

| Característica | Histogram | Summary |
|----------------|-----------|---------|
| Cálculo de cuantiles | Servidor (Prometheus) | Cliente (Python) |
| Agregación | ✅ Posible | ❌ No posible |
| Precisión | Aproximada | Exacta |
| Overhead CPU | Bajo | Alto |
| **Recomendación** | **Preferir** | Solo si necesitas cuantiles exactos |

---

## Categorías de Métricas

El sistema tiene **8 categorías** de métricas:

### 1. HTTP Metrics (`_init_http_metrics`)

Monitoriza requests HTTP de FastAPI.

```python
# Counters
http_requests_total            # Total de requests
http_requests_failed_total     # Requests fallidos (4xx/5xx)

# Histograms
http_request_duration_seconds  # Latencia de requests
http_request_size_bytes        # Tamaño de request body
http_response_size_bytes       # Tamaño de response body
```

**Uso típico:**
```python
# Al inicio del request
start_time = time.time()

# Al final del request
duration = time.time() - start_time
metrics.http_request_duration_seconds.labels(
    method="POST",
    endpoint="/api/videos"
).observe(duration)

metrics.http_requests_total.labels(
    method="POST",
    endpoint="/api/videos",
    status="201"
).inc()
```

### 2. Video Processing Metrics (`_init_video_metrics`)

Monitoriza el pipeline de procesamiento de videos.

```python
# Counters
videos_processed_total         # Total de videos procesados
audio_downloads_total          # Descargas de audio
transcriptions_total           # Transcripciones
summaries_total                # Resúmenes generados

# Histograms
video_processing_duration_seconds  # Duración por fase
audio_file_size_bytes          # Tamaño de archivos de audio
transcript_length_chars        # Longitud de transcripciones
summary_length_chars           # Longitud de resúmenes

# Gauge
active_video_processing        # Videos procesándose ahora
```

**Uso típico:**
```python
# Al inicio del procesamiento
metrics.active_video_processing.inc()
start_download = time.time()

# Después de descargar audio
download_duration = time.time() - start_download
metrics.video_processing_duration_seconds.labels(
    phase="download"
).observe(download_duration)

metrics.audio_downloads_total.labels(status="success").inc()

# Al finalizar
metrics.active_video_processing.dec()
metrics.videos_processed_total.labels(status="completed").inc()
```

### 3. Celery Metrics (`_init_celery_metrics`)

Monitoriza tareas asíncronas de Celery.

```python
# Counters
celery_task_total              # Total de tareas ejecutadas
celery_task_retries_total      # Total de reintentos

# Histograms
celery_task_duration_seconds   # Duración de tareas

# Gauges
celery_active_tasks            # Tareas ejecutándose ahora
celery_queue_size              # Tareas pendientes en cola
```

**Uso típico:**
```python
# Al inicio de la tarea
start_time = time.time()
metrics.celery_active_tasks.labels(task_name="process_video").inc()

# Al finalizar con éxito
duration = time.time() - start_time
metrics.celery_task_duration_seconds.labels(
    task_name="process_video"
).observe(duration)

metrics.celery_task_total.labels(
    task_name="process_video",
    status="success"
).inc()

metrics.celery_active_tasks.labels(task_name="process_video").dec()

# Al hacer retry
if self.request.retries > 0:
    metrics.celery_task_retries_total.labels(
        task_name="process_video"
    ).inc()
```

### 4. Cache Metrics (`_init_cache_metrics`)

Monitoriza operaciones de cache (Redis).

```python
# Counters
cache_hits_total               # Cache hits
cache_misses_total             # Cache misses

# Summaries
cache_operation_duration_seconds  # Duración de ops de cache

# Gauge
cache_size_bytes               # Tamaño del cache
```

**Uso típico:**
```python
# Cache hit
metrics.cache_hits_total.labels(cache_type="summary").inc()

# Cache miss
metrics.cache_misses_total.labels(cache_type="summary").inc()

# Actualizar tamaño
metrics.cache_size_bytes.labels(cache_type="summary").set(1024 * 1024 * 50)
```

**Hit rate (en Prometheus):**
```promql
sum(rate(cache_hits_total[5m])) /
(sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
```

### 5. Database Metrics (`_init_database_metrics`)

Monitoriza operaciones de base de datos.

```python
# Counters
db_queries_total               # Total de queries
db_connection_errors_total     # Errores de conexión

# Histograms
db_query_duration_seconds      # Duración de queries

# Gauge
db_connections_active          # Conexiones activas
```

### 6. API Errors Metrics (`_init_api_errors_metrics`)

Monitoriza errores de la API.

```python
# Counters
api_errors_total               # Total de errores por tipo
api_validation_errors_total    # Errores de validación
```

**Uso típico:**
```python
try:
    # ... código ...
except VideoNotFoundError:
    metrics.api_errors_total.labels(
        error_type="VideoNotFoundError",
        endpoint="/api/videos/{id}"
    ).inc()
    raise

except ValidationError:
    metrics.api_validation_errors_total.labels(
        field="youtube_url"
    ).inc()
    raise
```

### 7. External Services Metrics (`_init_external_services_metrics`)

Monitoriza llamadas a APIs externas.

```python
# Counters
external_api_requests_total    # Total de requests a APIs externas

# Histograms
external_api_duration_seconds  # Duración de requests
```

**Uso típico:**
```python
start_time = time.time()
try:
    response = await openai_client.chat.completions.create(...)
    duration = time.time() - start_time

    metrics.external_api_duration_seconds.labels(
        service="openai",
        operation="chat_completion"
    ).observe(duration)

    metrics.external_api_requests_total.labels(
        service="openai",
        operation="chat_completion",
        status="success"
    ).inc()
except Exception:
    metrics.external_api_requests_total.labels(
        service="openai",
        operation="chat_completion",
        status="error"
    ).inc()
    raise
```

### 8. System Metrics (`_init_system_metrics`)

Monitoriza recursos del sistema.

```python
# Gauges
cpu_usage_percent              # Uso de CPU
memory_usage_bytes             # Memoria RAM usada
disk_usage_bytes               # Espacio en disco usado
```

**Nota:** Estas métricas se obtienen típicamente de **Node Exporter** (ver `prometheus-operations.md`).

---

## Cómo Añadir Nuevas Métricas

### Paso 1: Identificar el Tipo de Métrica

Pregúntate:

1. **¿El valor solo puede crecer?** → `Counter`
   - Ejemplo: Total de errores, requests procesados

2. **¿El valor puede subir y bajar?** → `Gauge`
   - Ejemplo: Conexiones activas, memoria usada

3. **¿Necesitas distribución de valores?** → `Histogram`
   - Ejemplo: Latencias, tamaños de archivos

4. **¿Necesitas cuantiles exactos?** → `Summary` (raramente)
   - Preferir `Histogram` en la mayoría de casos

### Paso 2: Definir la Métrica en `src/core/metrics.py`

```python
class PrometheusMetrics:
    def _init_my_new_category_metrics(self):
        """Métricas para mi nueva categoría."""

        # Counter
        self.my_events_total = Counter(
            'my_events_total',
            'Total de eventos de mi categoría',
            ['event_type', 'status'],
            registry=self._registry
        )

        # Histogram
        self.my_operation_duration_seconds = Histogram(
            'my_operation_duration_seconds',
            'Duración de operaciones de mi categoría',
            ['operation_type'],
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0),
            registry=self._registry
        )

        # Gauge
        self.my_active_items = Gauge(
            'my_active_items',
            'Items activos de mi categoría',
            ['item_type'],
            registry=self._registry
        )

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        # ...
        self._init_my_new_category_metrics()
        # ...
```

### Paso 3: Usar la Métrica en el Código

```python
# En tu servicio
from src.core.metrics import metrics
import time

class MyService:
    async def process_item(self, item_type: str):
        # Incrementar gauge al inicio
        metrics.my_active_items.labels(item_type=item_type).inc()

        # Medir duración
        start_time = time.time()

        try:
            # ... tu lógica ...

            # Éxito
            metrics.my_events_total.labels(
                event_type="process",
                status="success"
            ).inc()

        except Exception as e:
            # Error
            metrics.my_events_total.labels(
                event_type="process",
                status="error"
            ).inc()
            raise

        finally:
            # Siempre registrar duración y decrementar gauge
            duration = time.time() - start_time
            metrics.my_operation_duration_seconds.labels(
                operation_type="process"
            ).observe(duration)

            metrics.my_active_items.labels(item_type=item_type).dec()
```

### Paso 4: Crear Tests

```python
# En tests/core/test_metrics.py
class TestMyNewCategoryMetrics:
    def test_my_events_total_exists(self):
        assert hasattr(metrics, 'my_events_total')
        assert isinstance(metrics.my_events_total, Counter)

    def test_my_events_total_labels(self):
        # Verificar que acepta los labels correctos
        metrics.my_events_total.labels(
            event_type="process",
            status="success"
        ).inc()

        # No debería fallar

    def test_my_operation_duration_histogram(self):
        assert hasattr(metrics, 'my_operation_duration_seconds')
        assert isinstance(metrics.my_operation_duration_seconds, Histogram)

        # Observar un valor
        metrics.my_operation_duration_seconds.labels(
            operation_type="process"
        ).observe(1.5)
```

### Paso 5: Validar en Prometheus

1. Arrancar servicios: `docker-compose up -d`
2. Arrancar app: `poetry run uvicorn src.api.main:app --reload`
3. Acceder a `http://localhost:8000/metrics`
4. Buscar tus métricas: `my_events_total`, `my_operation_duration_seconds`
5. Acceder a Prometheus: `http://localhost:9090`
6. Ejecutar query: `rate(my_events_total[5m])`

---

## Mejores Prácticas

### 1. Nombres de Métricas

✅ **Buenas prácticas:**
```python
http_requests_total              # Plural + _total
video_processing_duration_seconds  # Unidad clara
cache_hits_total                 # Verbo + sustantivo
```

❌ **Malas prácticas:**
```python
request                          # Singular
video_time                       # Unidad ambigua
hits                             # Contexto poco claro
```

**Convenciones:**
- Snake_case minúsculas
- Prefijo del dominio: `http_`, `celery_`, `db_`
- Sufijos estándar: `_total`, `_seconds`, `_bytes`, `_percent`
- Nombres descriptivos y sin ambigüedad

### 2. Labels (Etiquetas)

✅ **Buenas prácticas:**
```python
# Baja cardinalidad
metrics.http_requests_total.labels(
    method="GET",           # ~10 valores posibles
    endpoint="/api/videos", # ~50 endpoints
    status="200"            # ~20 códigos HTTP
).inc()
# Cardinalidad total: 10 × 50 × 20 = 10,000 series
```

❌ **Malas prácticas:**
```python
# ⚠️ ALTA CARDINALIDAD - NUNCA HACER ESTO
metrics.http_requests_total.labels(
    user_id="123e4567-...",      # Millones de usuarios
    video_id="456f7890-...",     # Millones de videos
    timestamp="2025-11-15T10:30" # Infinitos valores
).inc()
# Cardinalidad total: ∞ → CRASH de Prometheus
```

**Reglas de oro:**
- Máximo **10,000 series** por métrica (idealmente < 1,000)
- Evitar IDs únicos (user_id, video_id, request_id)
- Evitar timestamps o valores continuos
- Preferir **categorías** en lugar de valores únicos

**Tabla de cardinalidad aceptable:**

| Label | Valores típicos | Cardinalidad | ✅/❌ |
|-------|-----------------|--------------|------|
| `method` | GET, POST, PUT, DELETE | ~10 | ✅ |
| `status` | 200, 201, 400, 404, 500 | ~20 | ✅ |
| `endpoint` | /api/videos, /api/summaries | ~50 | ✅ |
| `error_type` | VideoNotFoundError, ... | ~30 | ✅ |
| `user_id` | UUID único por usuario | 1,000,000+ | ❌ |
| `timestamp` | Valor continuo | ∞ | ❌ |

### 3. Granularidad de Métricas

**No sobre-instrumentar:**

❌ **Demasiadas métricas:**
```python
# Una métrica por cada función
video_download_start_total
video_download_end_total
video_download_validate_total
video_download_cleanup_total
# ...50 métricas más
```

✅ **Métricas consolidadas:**
```python
# Una métrica con labels
video_processing_duration_seconds{phase="download"}
video_processing_duration_seconds{phase="transcription"}
video_processing_duration_seconds{phase="summary"}
video_processing_duration_seconds{phase="total"}
```

**Regla del 80/20:**
- 20% de métricas cubren 80% de necesidades
- Empezar con métricas de alto nivel
- Añadir detalle solo cuando se detecta un problema específico

### 4. Documentación de Métricas

**Siempre incluir docstring descriptivo:**

```python
self.http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'Duración de requests HTTP desde que se recibe hasta que se envía respuesta. '
    'Incluye tiempo de procesamiento, DB queries y llamadas externas. '
    'Labels: method (GET/POST/etc), endpoint (ruta de la API)',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=self._registry
)
```

### 5. Gestión de Errores

**Siempre registrar métricas en bloques `try/finally`:**

```python
start_time = time.time()
metrics.active_video_processing.inc()

try:
    # ... procesamiento ...
    metrics.videos_processed_total.labels(status="success").inc()
except Exception as e:
    metrics.videos_processed_total.labels(status="error").inc()
    metrics.api_errors_total.labels(
        error_type=type(e).__name__,
        endpoint="/api/videos"
    ).inc()
    raise
finally:
    # Siempre se ejecuta
    duration = time.time() - start_time
    metrics.video_processing_duration_seconds.labels(
        phase="total"
    ).observe(duration)
    metrics.active_video_processing.dec()
```

### 6. Buckets de Histogramas

**Adaptar buckets al rango esperado de valores:**

```python
# Para latencias de API (milisegundos a segundos)
buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# Para procesamiento de videos (segundos a minutos)
buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)

# Para tamaños de archivos (KB a MB)
buckets=(1024, 10240, 102400, 1048576, 10485760, 104857600)
```

**Reglas:**
- Incluir valores típicos (p50, p90, p99)
- Distribución logarítmica (×2, ×5, ×10)
- Siempre incluye `+Inf` (automático)

---

## Troubleshooting

### Problema 1: Error "Duplicated timeseries"

**Error:**
```
ValueError: Duplicated timeseries in CollectorRegistry: {'cache_hits_total', 'cache_hits_created'}
```

**Causa:**
Estás registrando la misma métrica dos veces en el mismo registry.

**Solución:**
```python
# ❌ MAL: Crear métrica local
cache_hits = Counter("cache_hits_total", ...)

# ✅ BIEN: Usar métrica centralizada
from src.core.metrics import metrics
metrics.cache_hits_total.labels(...).inc()
```

### Problema 2: Métricas no aparecen en `/metrics`

**Causas posibles:**

1. **No has importado `metrics`:**
   ```python
   # En src/api/main.py
   from src.core.metrics import metrics  # ← Importante
   ```

2. **No has registrado la métrica:**
   - Verifica que la métrica está en `src/core/metrics.py`
   - Verifica que el método `_init_*` está siendo llamado en `__init__`

3. **No has usado la métrica:**
   - Las métricas solo aparecen después del primer uso
   - Ejemplo: `metrics.my_metric.labels(...).inc()` debe ejecutarse al menos una vez

**Debug:**
```bash
# Ver todas las métricas disponibles
curl http://localhost:8000/metrics | grep "my_metric"

# Ver si la métrica está en el registry
python -c "from src.core.metrics import metrics; print(metrics.my_metric)"
```

### Problema 3: Prometheus no scrapea métricas

**Causas posibles:**

1. **Servicio FastAPI no está corriendo:**
   ```bash
   curl http://localhost:8000/metrics
   # Debe retornar métricas, no error de conexión
   ```

2. **Prometheus no puede alcanzar FastAPI:**
   ```yaml
   # En prometheus.yml, verificar target
   static_configs:
     - targets: ['host.docker.internal:8000']  # Linux/WSL
     # - targets: ['host.docker.internal:8000']  # macOS/Windows
   ```

3. **Verificar estado en Prometheus:**
   - Acceder a `http://localhost:9090/targets`
   - Verificar que `fastapi` tiene estado `UP`

**Solución:**
```bash
# Verificar conectividad desde container de Prometheus
docker exec -it iamonitor_prometheus wget -O- http://host.docker.internal:8000/metrics
```

### Problema 4: Cardinalidad demasiado alta

**Síntoma:**
Prometheus consume mucha RAM o se vuelve lento.

**Diagnóstico:**
```promql
# Ver métricas con más series
topk(10, count by (__name__)({__name__=~".+"}))
```

**Solución:**
- Revisar labels con alta cardinalidad (IDs únicos)
- Reemplazar IDs por categorías
- Usar `relabel_config` en Prometheus para eliminar labels

### Problema 5: Tests fallan con "Duplicated timeseries"

**Causa:**
El singleton de `PrometheusMetrics` persiste entre tests.

**Solución:**
```python
# En tests/core/test_metrics.py
import pytest
from prometheus_client import CollectorRegistry

@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics singleton antes de cada test."""
    from src.core.metrics import PrometheusMetrics
    PrometheusMetrics._instance = None
    yield
    PrometheusMetrics._instance = None
```

---

## Recursos Adicionales

- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [PromQL Cheat Sheet](prometheus-queries.md)
- [Guía de Operaciones](prometheus-operations.md)

---

**Siguiente:** [Queries PromQL útiles](prometheus-queries.md)
