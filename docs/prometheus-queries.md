# Guía de Queries PromQL: YouTube AI Summary

**Proyecto:** youtube-AIsummary
**Paso:** 22 - Sistema de Métricas
**Última actualización:** 15/11/2025

---

## 📋 Tabla de Contenidos

1. [Introducción a PromQL](#introducción-a-promql)
2. [Queries HTTP y API](#queries-http-y-api)
3. [Queries de Procesamiento de Videos](#queries-de-procesamiento-de-videos)
4. [Queries de Celery](#queries-de-celery)
5. [Queries de Cache](#queries-de-cache)
6. [Queries de Base de Datos](#queries-de-base-de-datos)
7. [Queries de Sistema](#queries-de-sistema)
8. [Alerting Rules](#alerting-rules)
9. [Recording Rules](#recording-rules)
10. [Tips y Trucos](#tips-y-trucos)

---

## Introducción a PromQL

**PromQL** (Prometheus Query Language) es el lenguaje de consulta de Prometheus.

### Conceptos Básicos

#### Instant Vector
Un único valor por serie temporal en el momento actual.

```promql
# Valor actual de requests HTTP
http_requests_total

# Con filtro por labels
http_requests_total{method="GET"}

# Múltiples labels
http_requests_total{method="GET", status="200"}
```

#### Range Vector
Valores de una serie temporal durante un rango de tiempo.

```promql
# Últimos 5 minutos de requests
http_requests_total[5m]

# Últimas 24 horas
http_requests_total[24h]
```

#### Operadores Principales

| Operador | Función | Ejemplo |
|----------|---------|---------|
| `rate()` | Tasa por segundo | `rate(http_requests_total[5m])` |
| `irate()` | Tasa instantánea | `irate(http_requests_total[5m])` |
| `increase()` | Incremento total | `increase(http_requests_total[1h])` |
| `sum()` | Suma | `sum(http_requests_total)` |
| `avg()` | Promedio | `avg(http_request_duration_seconds)` |
| `max()` | Máximo | `max(memory_usage_bytes)` |
| `min()` | Mínimo | `min(cpu_usage_percent)` |
| `count()` | Conteo | `count(http_requests_total)` |

#### Agregación

```promql
# Sumar todas las series (elimina todos los labels)
sum(http_requests_total)

# Sumar agrupando por método
sum by (method) (http_requests_total)

# Promediar agrupando por endpoint
avg by (endpoint) (http_request_duration_seconds)
```

---

## Queries HTTP y API

### 1. Request Rate (Requests por segundo)

**Total de requests/s:**
```promql
sum(rate(http_requests_total[5m]))
```

**Requests/s por endpoint:**
```promql
sum by (endpoint) (rate(http_requests_total[5m]))
```

**Requests/s por método:**
```promql
sum by (method) (rate(http_requests_total[5m]))
```

**Top 5 endpoints más solicitados:**
```promql
topk(5, sum by (endpoint) (rate(http_requests_total[5m])))
```

### 2. Error Rate (Tasa de errores)

**Porcentaje de errores (4xx + 5xx):**
```promql
(
  sum(rate(http_requests_total{status=~"4..|5.."}[5m]))
  /
  sum(rate(http_requests_total[5m]))
) * 100
```

**Errores/s por código de estado:**
```promql
sum by (status) (rate(http_requests_total{status=~"4..|5.."}[5m]))
```

**Top 5 endpoints con más errores:**
```promql
topk(5,
  sum by (endpoint) (rate(http_requests_total{status=~"4..|5.."}[5m]))
)
```

### 3. Latencia (Response Time)

**Latencia promedio (últimos 5 minutos):**
```promql
avg(rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]))
```

**Latencia p50 (mediana):**
```promql
histogram_quantile(0.5,
  rate(http_request_duration_seconds_bucket[5m])
)
```

**Latencia p95:**
```promql
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m])
)
```

**Latencia p99:**
```promql
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m])
)
```

**Latencia p99 por endpoint:**
```promql
histogram_quantile(0.99,
  sum by (endpoint, le) (rate(http_request_duration_seconds_bucket[5m]))
)
```

**Top 5 endpoints más lentos (p95):**
```promql
topk(5,
  histogram_quantile(0.95,
    sum by (endpoint, le) (rate(http_request_duration_seconds_bucket[5m]))
  )
)
```

### 4. Throughput

**Requests totales en la última hora:**
```promql
increase(http_requests_total[1h])
```

**Bytes enviados/s:**
```promql
sum(rate(http_response_size_bytes_sum[5m]))
```

**Bytes recibidos/s:**
```promql
sum(rate(http_request_size_bytes_sum[5m]))
```

### 5. SLA / Availability

**Uptime (% de requests exitosos en 24h):**
```promql
(
  sum(increase(http_requests_total{status=~"2.."}[24h]))
  /
  sum(increase(http_requests_total[24h]))
) * 100
```

**Requests que cumplen SLA (<1s):**
```promql
(
  sum(rate(http_request_duration_seconds_bucket{le="1.0"}[5m]))
  /
  sum(rate(http_request_duration_seconds_count[5m]))
) * 100
```

---

## Queries de Procesamiento de Videos

### 1. Videos Procesados

**Videos procesados/minuto:**
```promql
sum(rate(videos_processed_total[5m])) * 60
```

**Videos procesados en las últimas 24h:**
```promql
increase(videos_processed_total[24h])
```

**Videos completados vs fallidos:**
```promql
sum by (status) (increase(videos_processed_total[1h]))
```

**Tasa de éxito (%):**
```promql
(
  sum(rate(videos_processed_total{status="completed"}[5m]))
  /
  sum(rate(videos_processed_total[5m]))
) * 100
```

### 2. Duración del Pipeline

**Tiempo promedio de procesamiento completo:**
```promql
avg(rate(video_processing_duration_seconds_sum{phase="total"}[5m]) / rate(video_processing_duration_seconds_count{phase="total"}[5m]))
```

**Tiempo promedio por fase:**
```promql
avg by (phase) (
  rate(video_processing_duration_seconds_sum[5m]) /
  rate(video_processing_duration_seconds_count[5m])
)
```

**p95 de tiempo de descarga:**
```promql
histogram_quantile(0.95,
  rate(video_processing_duration_seconds_bucket{phase="download"}[5m])
)
```

**p99 de tiempo de transcripción:**
```promql
histogram_quantile(0.99,
  rate(video_processing_duration_seconds_bucket{phase="transcription"}[5m])
)
```

**Fase más lenta (promedio):**
```promql
topk(1,
  avg by (phase) (
    rate(video_processing_duration_seconds_sum[5m]) /
    rate(video_processing_duration_seconds_count[5m])
  )
)
```

### 3. Tamaños de Archivos

**Tamaño promedio de archivos de audio (MB):**
```promql
avg(rate(audio_file_size_bytes_sum[5m]) / rate(audio_file_size_bytes_count[5m])) / 1024 / 1024
```

**p95 de tamaño de archivos:**
```promql
histogram_quantile(0.95,
  rate(audio_file_size_bytes_bucket[5m])
) / 1024 / 1024
```

### 4. Longitudes de Texto

**Longitud promedio de transcripciones:**
```promql
avg(rate(transcript_length_chars_sum[5m]) / rate(transcript_length_chars_count[5m]))
```

**Longitud promedio de resúmenes:**
```promql
avg(rate(summary_length_chars_sum[5m]) / rate(summary_length_chars_count[5m]))
```

**Ratio de compresión (resumen / transcripción):**
```promql
(
  avg(rate(summary_length_chars_sum[5m]) / rate(summary_length_chars_count[5m]))
  /
  avg(rate(transcript_length_chars_sum[5m]) / rate(transcript_length_chars_count[5m]))
) * 100
```

### 5. Concurrencia

**Videos procesándose ahora mismo:**
```promql
active_video_processing
```

**Máximo de videos procesados simultáneamente (última hora):**
```promql
max_over_time(active_video_processing[1h])
```

---

## Queries de Celery

### 1. Task Rate

**Tareas ejecutadas/minuto:**
```promql
sum(rate(celery_task_total[5m])) * 60
```

**Tareas por nombre:**
```promql
sum by (task_name) (rate(celery_task_total[5m]))
```

**Tareas exitosas vs fallidas:**
```promql
sum by (status) (rate(celery_task_total[5m]))
```

**Tasa de éxito (%):**
```promql
(
  sum(rate(celery_task_total{status="success"}[5m]))
  /
  sum(rate(celery_task_total[5m]))
) * 100
```

### 2. Task Duration

**Duración promedio de tareas:**
```promql
avg by (task_name) (
  rate(celery_task_duration_seconds_sum[5m]) /
  rate(celery_task_duration_seconds_count[5m])
)
```

**p95 de duración por tarea:**
```promql
histogram_quantile(0.95,
  sum by (task_name, le) (rate(celery_task_duration_seconds_bucket[5m]))
)
```

**Tarea más lenta (p99):**
```promql
topk(1,
  histogram_quantile(0.99,
    sum by (task_name, le) (rate(celery_task_duration_seconds_bucket[5m]))
  )
)
```

### 3. Queue Health

**Tamaño de cola por nombre:**
```promql
celery_queue_size
```

**Tareas activas ejecutándose ahora:**
```promql
sum(celery_active_tasks)
```

**Tareas activas por tipo:**
```promql
sum by (task_name) (celery_active_tasks)
```

### 4. Retries

**Reintentos/minuto:**
```promql
sum(rate(celery_task_retries_total[5m])) * 60
```

**Reintentos por tarea:**
```promql
sum by (task_name) (rate(celery_task_retries_total[5m]))
```

**Ratio de reintentos (%):**
```promql
(
  sum(rate(celery_task_retries_total[5m]))
  /
  sum(rate(celery_task_total[5m]))
) * 100
```

### 5. Worker Health

**Predicción: ¿La cola crecerá en la próxima hora?**
```promql
predict_linear(celery_queue_size[30m], 3600) > 100
```

**Tiempo estimado para vaciar la cola (minutos):**
```promql
celery_queue_size / (sum(rate(celery_task_total[5m])) * 60)
```

---

## Queries de Cache

### 1. Hit Rate

**Hit rate (%):**
```promql
(
  sum(rate(cache_hits_total[5m]))
  /
  (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
) * 100
```

**Hit rate por tipo de cache:**
```promql
(
  sum by (cache_type) (rate(cache_hits_total[5m]))
  /
  (sum by (cache_type) (rate(cache_hits_total[5m])) + sum by (cache_type) (rate(cache_misses_total[5m])))
) * 100
```

**Miss rate (%):**
```promql
(
  sum(rate(cache_misses_total[5m]))
  /
  (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
) * 100
```

### 2. Cache Operations

**Operaciones de cache/s:**
```promql
sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))
```

**Hits/s:**
```promql
sum(rate(cache_hits_total[5m]))
```

**Misses/s:**
```promql
sum(rate(cache_misses_total[5m]))
```

### 3. Cache Performance

**Duración promedio de operaciones:**
```promql
avg(rate(cache_operation_duration_seconds_sum[5m]) / rate(cache_operation_duration_seconds_count[5m]))
```

**Duración promedio por operación:**
```promql
avg by (operation) (
  rate(cache_operation_duration_seconds_sum[5m]) /
  rate(cache_operation_duration_seconds_count[5m])
)
```

### 4. Cache Size

**Tamaño del cache (MB):**
```promql
cache_size_bytes / 1024 / 1024
```

**Tamaño del cache por tipo:**
```promql
sum by (cache_type) (cache_size_bytes) / 1024 / 1024
```

---

## Queries de Base de Datos

### 1. Query Performance

**Queries/s:**
```promql
sum(rate(db_queries_total[5m]))
```

**Queries/s por operación:**
```promql
sum by (operation) (rate(db_queries_total[5m]))
```

**Duración promedio de queries:**
```promql
avg(rate(db_query_duration_seconds_sum[5m]) / rate(db_query_duration_seconds_count[5m]))
```

**p99 de latencia de queries:**
```promql
histogram_quantile(0.99,
  rate(db_query_duration_seconds_bucket[5m])
)
```

**Queries lentas (>100ms):**
```promql
sum(rate(db_query_duration_seconds_bucket{le="0.1"}[5m])) < bool
sum(rate(db_query_duration_seconds_count[5m]))
```

### 2. Connections

**Conexiones activas:**
```promql
db_connections_active
```

**Máximo de conexiones (última hora):**
```promql
max_over_time(db_connections_active[1h])
```

**Pool saturation (si tienes max_connections configurado):**
```promql
(db_connections_active / 100) * 100  # Asumiendo max_connections=100
```

### 3. Errors

**Errores de conexión/minuto:**
```promql
sum(rate(db_connection_errors_total[5m])) * 60
```

**Tasa de errores (%):**
```promql
(
  sum(rate(db_connection_errors_total[5m]))
  /
  sum(rate(db_queries_total[5m]))
) * 100
```

---

## Queries de Sistema

### 1. CPU

**CPU usage (%):**
```promql
cpu_usage_percent
```

**CPU promedio (última hora):**
```promql
avg_over_time(cpu_usage_percent[1h])
```

**CPU p95 (última hora):**
```promql
quantile_over_time(0.95, cpu_usage_percent[1h])
```

### 2. Memory

**Memoria usada (GB):**
```promql
memory_usage_bytes / 1024 / 1024 / 1024
```

**Memoria usada (%):**
```promql
(memory_usage_bytes / (8 * 1024 * 1024 * 1024)) * 100  # Asumiendo 8GB RAM
```

**Memoria libre (GB):**
```promql
(8 * 1024 * 1024 * 1024 - memory_usage_bytes) / 1024 / 1024 / 1024
```

### 3. Disk

**Disco usado (GB):**
```promql
disk_usage_bytes / 1024 / 1024 / 1024
```

**Disco usado (%):**
```promql
(disk_usage_bytes / (240 * 1024 * 1024 * 1024)) * 100  # Asumiendo disco de 240GB
```

---

## Alerting Rules

Configuración de alertas en `prometheus/alert_rules.yml`:

### 1. API Alerts

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      # Alta tasa de errores
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Alta tasa de errores (>5%)"
          description: "{{ $value | humanizePercentage }} de requests están fallando"

      # Latencia alta
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 2.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Latencia p95 >2s"
          description: "Latencia p95 es {{ $value }}s"

      # Baja disponibilidad
      - alert: LowAvailability
        expr: |
          (
            sum(rate(http_requests_total{status=~"2.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) < 0.95
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disponibilidad <95%"
          description: "Solo {{ $value | humanizePercentage }} de requests son exitosos"
```

### 2. Video Processing Alerts

```yaml
  - name: video_processing_alerts
    interval: 30s
    rules:
      # Alta tasa de fallos en procesamiento
      - alert: HighVideoProcessingFailureRate
        expr: |
          (
            sum(rate(videos_processed_total{status="failed"}[10m]))
            /
            sum(rate(videos_processed_total[10m]))
          ) > 0.20
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Alta tasa de fallos en videos (>20%)"
          description: "{{ $value | humanizePercentage }} de videos están fallando"

      # Procesamiento muy lento
      - alert: SlowVideoProcessing
        expr: |
          histogram_quantile(0.95,
            rate(video_processing_duration_seconds_bucket{phase="total"}[10m])
          ) > 600
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Procesamiento de videos muy lento (p95 >10min)"
          description: "p95 de procesamiento es {{ $value }}s"

      # Muchos videos procesándose simultáneamente
      - alert: TooManyActiveVideos
        expr: active_video_processing > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Demasiados videos procesándose simultáneamente"
          description: "{{ $value }} videos activos (límite esperado: 10)"
```

### 3. Celery Alerts

```yaml
  - name: celery_alerts
    interval: 30s
    rules:
      # Cola creciendo
      - alert: CeleryQueueGrowing
        expr: |
          predict_linear(celery_queue_size[30m], 3600) > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cola de Celery creciendo rápidamente"
          description: "Se predice {{ $value }} tareas en 1h"

      # Alta tasa de reintentos
      - alert: HighCeleryRetryRate
        expr: |
          (
            sum(rate(celery_task_retries_total[5m]))
            /
            sum(rate(celery_task_total[5m]))
          ) > 0.10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Alta tasa de reintentos Celery (>10%)"
          description: "{{ $value | humanizePercentage }} de tareas requieren retry"

      # Tareas muy lentas
      - alert: SlowCeleryTasks
        expr: |
          histogram_quantile(0.95,
            rate(celery_task_duration_seconds_bucket[10m])
          ) > 300
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Tareas Celery muy lentas (p95 >5min)"
          description: "p95 de duración es {{ $value }}s"
```

### 4. Cache Alerts

```yaml
  - name: cache_alerts
    interval: 30s
    rules:
      # Bajo hit rate
      - alert: LowCacheHitRate
        expr: |
          (
            sum(rate(cache_hits_total[10m]))
            /
            (sum(rate(cache_hits_total[10m])) + sum(rate(cache_misses_total[10m])))
          ) < 0.70
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Hit rate de cache bajo (<70%)"
          description: "Hit rate es {{ $value | humanizePercentage }}"
```

### 5. System Alerts

```yaml
  - name: system_alerts
    interval: 30s
    rules:
      # CPU alta
      - alert: HighCPU
        expr: cpu_usage_percent > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CPU usage alto (>80%)"
          description: "CPU usage es {{ $value }}%"

      # Memoria alta
      - alert: HighMemory
        expr: (memory_usage_bytes / (8 * 1024 * 1024 * 1024)) * 100 > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Memoria usage alto (>85%)"
          description: "Memoria usage es {{ $value }}%"

      # Disco casi lleno
      - alert: DiskAlmostFull
        expr: (disk_usage_bytes / (240 * 1024 * 1024 * 1024)) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disco casi lleno (>90%)"
          description: "Disco usage es {{ $value }}%"
```

---

## Recording Rules

Reglas de grabación para pre-calcular queries complejas en `prometheus/recording_rules.yml`:

```yaml
groups:
  - name: recording_rules
    interval: 30s
    rules:
      # HTTP
      - record: job:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m]))

      - record: job:http_error_rate:rate5m
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))

      - record: job:http_latency_p95:5m
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          )

      # Videos
      - record: job:videos_processed:rate5m
        expr: sum(rate(videos_processed_total[5m]))

      - record: job:video_success_rate:rate5m
        expr: |
          sum(rate(videos_processed_total{status="completed"}[5m]))
          /
          sum(rate(videos_processed_total[5m]))

      # Celery
      - record: job:celery_tasks:rate5m
        expr: sum(rate(celery_task_total[5m]))

      - record: job:celery_success_rate:rate5m
        expr: |
          sum(rate(celery_task_total{status="success"}[5m]))
          /
          sum(rate(celery_task_total[5m]))

      # Cache
      - record: job:cache_hit_rate:rate5m
        expr: |
          sum(rate(cache_hits_total[5m]))
          /
          (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
```

**Uso de recording rules:**
```promql
# En lugar de query compleja
sum(rate(http_requests_total[5m]))

# Usar recording rule (más rápido)
job:http_requests:rate5m
```

---

## Tips y Trucos

### 1. Debugging de Queries

**Ver todas las métricas disponibles:**
```promql
{__name__=~".+"}
```

**Ver métricas de un job específico:**
```promql
{job="fastapi"}
```

**Ver series con un label específico:**
```promql
{endpoint="/api/videos"}
```

### 2. Time Ranges

```promql
# Últimos N minutos
[5m]   # 5 minutos
[1h]   # 1 hora
[24h]  # 24 horas
[7d]   # 7 días

# Offset (datos de hace X tiempo)
http_requests_total offset 1h   # Hace 1 hora
http_requests_total offset 1d   # Hace 1 día
```

### 3. Comparaciones Temporales

**Comparar tráfico actual vs hace 1 hora:**
```promql
sum(rate(http_requests_total[5m]))
/
sum(rate(http_requests_total[5m] offset 1h))
```

**Cambio porcentual respecto a ayer:**
```promql
(
  (sum(rate(http_requests_total[5m])) - sum(rate(http_requests_total[5m] offset 24h)))
  /
  sum(rate(http_requests_total[5m] offset 24h))
) * 100
```

### 4. Agregaciones Útiles

**Top K:**
```promql
# Top 10 endpoints
topk(10, sum by (endpoint) (rate(http_requests_total[5m])))
```

**Bottom K:**
```promql
# 5 endpoints menos usados
bottomk(5, sum by (endpoint) (rate(http_requests_total[5m])))
```

**Count distinct:**
```promql
# Número de endpoints únicos
count(count by (endpoint) (http_requests_total))
```

### 5. Expresiones Booleanas

**Alerting condicional:**
```promql
# 1 si error rate >5%, 0 en caso contrario
(
  sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
  sum(rate(http_requests_total[5m]))
) > 0.05
```

**AND lógico:**
```promql
(cpu_usage_percent > 80) and (memory_usage_bytes > 6 * 1024 * 1024 * 1024)
```

**OR lógico:**
```promql
(cpu_usage_percent > 90) or (memory_usage_bytes > 7 * 1024 * 1024 * 1024)
```

### 6. Funciones de Agregación Temporal

```promql
# Máximo en ventana de tiempo
max_over_time(cpu_usage_percent[1h])

# Mínimo
min_over_time(cpu_usage_percent[1h])

# Promedio
avg_over_time(cpu_usage_percent[1h])

# Cuantil (p95)
quantile_over_time(0.95, cpu_usage_percent[1h])
```

### 7. Formateo en Grafana

**Humanizar bytes:**
```promql
# MB
cache_size_bytes / 1024 / 1024

# Grafana automáticamente formatea con unidad "bytes"
```

**Humanizar duración:**
```promql
# Grafana automáticamente formatea con unidad "seconds"
avg(rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]))
```

---

## Recursos Adicionales

- [PromQL Official Docs](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Grafana Dashboard Gallery](https://grafana.com/grafana/dashboards/)

---

**Siguiente:** [Guía de Operaciones](prometheus-operations.md)
