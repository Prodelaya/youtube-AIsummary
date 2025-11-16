# Guía de Dashboards de Grafana

**Proyecto:** YouTube AI Summary
**Versión:** 1.0
**Fecha:** 15/11/2025
**Paso del Roadmap:** Paso 23 - Grafana Dashboard

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Acceso a Grafana](#acceso-a-grafana)
3. [Dashboards Disponibles](#dashboards-disponibles)
4. [Dashboard: System Overview](#dashboard-system-overview)
5. [Dashboard: API Performance](#dashboard-api-performance)
6. [Dashboard: Video Processing Pipeline](#dashboard-video-processing-pipeline)
7. [Alertas Configuradas](#alertas-configuradas)
8. [Troubleshooting](#troubleshooting)
9. [Operaciones Avanzadas](#operaciones-avanzadas)

---

## 🎯 Introducción

Los dashboards de Grafana proporcionan visualización en tiempo real de las métricas del sistema YouTube AI Summary. Integrados con Prometheus, permiten:

- **Monitoreo continuo** del estado del sistema
- **Identificación rápida** de problemas de rendimiento
- **Análisis histórico** de tendencias (hasta 15 días)
- **Alertas visuales** mediante thresholds configurados

### Arquitectura de Observabilidad

```
┌─────────────────┐
│   FastAPI App   │ ──► Expone métricas /metrics
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   Prometheus    │ ──► Scrape cada 15s, retención 15 días
└─────────────────┘
         │
         ▼
┌─────────────────┐
│     Grafana     │ ──► Visualización de dashboards
└─────────────────┘
```

---

## 🔐 Acceso a Grafana

### URL y Credenciales

- **URL:** http://localhost:3000
- **Usuario por defecto:** `admin`
- **Contraseña por defecto:** `dev_grafana_2024`

> ⚠️ **IMPORTANTE:** Cambia la contraseña al primer login en producción.

### Cambiar Contraseña

#### Desde la UI

1. Acceder a http://localhost:3000
2. Login con credenciales por defecto
3. Ir a **Profile → Change Password**
4. Introducir nueva contraseña

#### Desde Variables de Entorno

Editar `.env`:

```bash
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=tu_password_segura_aqui
```

Reiniciar Grafana:

```bash
docker-compose restart grafana
```

---

## 📊 Dashboards Disponibles

El sistema incluye **3 dashboards** organizados en la carpeta **"YouTube AI Summary"**:

| Dashboard                     | UID                           | Paneles | Descripción                            |
| ----------------------------- | ----------------------------- | ------- | -------------------------------------- |
| **System Overview**           | `youtube-ai-system-overview`  | 8       | Vista general del estado del sistema   |
| **API Performance**           | `youtube-ai-api-performance`  | 6       | Métricas de rendimiento de la API REST |
| **Video Processing Pipeline** | `youtube-ai-video-processing` | 8       | Análisis del pipeline de procesamiento |

### Navegación

1. Acceder a Grafana → **Dashboards**
2. Abrir carpeta **YouTube AI Summary**
3. Seleccionar el dashboard deseado

---

## 📈 Dashboard: System Overview

**UID:** `youtube-ai-system-overview`
**Tags:** `youtube-ai`, `overview`, `system`
**Refresh:** 15 segundos
**Time Range:** Últimas 6 horas

### Objetivo

Proporcionar una vista 360° del estado del sistema en tiempo real, incluyendo procesamiento de videos, API, colas de trabajo y recursos.

### Paneles

#### 1. Total Videos Processed

**Tipo:** Stat
**Query:** `sum(videos_processed_total)`

- **Descripción:** Contador total de videos procesados (completados + fallidos).
- **Valores normales:** Incremento constante.
- **⚠️ Anomalía:** Sin incremento durante >1 hora → revisar workers.

---

#### 2. Videos Processing Rate (videos/min)

**Tipo:** Stat
**Query:** `sum(rate(videos_processed_total{status="completed"}[5m])) * 60`

- **Descripción:** Velocidad de procesamiento de videos completados.
- **Valores normales:** 0.5 - 2 videos/minuto (depende de carga).
- **Thresholds:**
  - Verde: < 0.5
  - Amarillo: 0.5 - 1.0
  - Rojo: > 1.0

---

#### 3. Success Rate (%)

**Tipo:** Gauge
**Query:** `sum(rate(videos_processed_total{status="completed"}[5m])) / sum(rate(videos_processed_total[5m])) * 100`

- **Descripción:** Porcentaje de videos completados exitosamente.
- **Valores normales:** > 95%
- **Thresholds:**
  - Rojo: < 80%
  - Amarillo: 80-95%
  - Verde: > 95%
- **⚠️ Anomalía:** < 80% → revisar logs de errores.

---

#### 4. Cache Hit Rate (%)

**Tipo:** Gauge
**Query:** `sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))) * 100`

- **Descripción:** Efectividad del cache Redis.
- **Valores normales:** > 80%
- **Thresholds:**
  - Rojo: < 50%
  - Amarillo: 50-80%
  - Verde: > 80%
- **⚠️ Anomalía:** < 50% → cache frío o TTL muy corto.

---

#### 5. API Requests per Second (by method)

**Tipo:** Time Series
**Query:** `sum(rate(http_requests_total[1m])) by (method)`

- **Descripción:** Requests/segundo desglosados por método HTTP.
- **Valores normales:** GET > POST (consultas más frecuentes).
- **Calcs mostrados:** Mean, Max

---

#### 6. Celery Queue Size (by queue)

**Tipo:** Bar Gauge
**Query:** `sum(celery_tasks_active) by (queue)`

- **Descripción:** Tareas activas en colas Celery.
- **Valores normales:** < 30 tareas.
- **Thresholds:**
  - Verde: < 30
  - Amarillo: 30-50
  - Rojo: > 50
- **⚠️ Anomalía:** > 50 → worker sobrecargado o bloqueado.

---

#### 7. System Resources (FastAPI)

**Tipo:** Time Series (dual axis)
**Queries:**

- Memoria: `process_resident_memory_bytes{job="fastapi"}`
- CPU: `rate(process_cpu_seconds_total{job="fastapi"}[1m])`

- **Descripción:** Uso de CPU y RAM del proceso FastAPI.
- **Valores normales:**
  - Memoria: 200-500 MB
  - CPU: 10-30%
- **⚠️ Anomalía:**
  - Memoria > 1 GB → posible memory leak.
  - CPU > 80% → saturación de workers.

---

#### 8. HTTP 5xx Error Rate

**Tipo:** Time Series
**Query:** `sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))`

- **Descripción:** Tasa de errores 5xx (server errors).
- **Valores normales:** < 1%
- **Threshold:** Línea roja en 5%
- **⚠️ Anomalía:** > 5% → revisar logs inmediatamente.

---

## 🚀 Dashboard: API Performance

**UID:** `youtube-ai-api-performance`
**Tags:** `youtube-ai`, `api`, `performance`
**Refresh:** 15 segundos
**Time Range:** Últimas 6 horas

### Objetivo

Analizar el rendimiento de la API REST, identificar endpoints lentos y monitorear latencias.

### Paneles

#### 1. Request Rate by Endpoint

**Tipo:** Time Series
**Query:** `sum(rate(http_requests_total[1m])) by (endpoint)`

- **Descripción:** Requests/segundo por endpoint.
- **Valores normales:** `/videos/process` más activo.
- **Calcs:** Mean, Max

---

#### 2. HTTP Status Codes Distribution

**Tipo:** Time Series (stacked)
**Query:** `sum(rate(http_requests_total[1m])) by (status)`

- **Descripción:** Distribución de códigos HTTP.
- **Colores:**
  - 2xx: Verde (éxito)
  - 4xx: Amarillo (client error)
  - 5xx: Rojo (server error)
- **Valores normales:** > 95% códigos 2xx.

---

#### 3. Request Latency p95 (by endpoint)

**Tipo:** Time Series
**Query:** `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))`

- **Descripción:** Percentil 95 de latencia por endpoint.
- **Valores normales:** < 2 segundos.
- **Thresholds:**
  - Verde: < 1s
  - Amarillo: 1-2s
  - Rojo: > 2s
- **⚠️ Anomalía:** > 2s → endpoint lento, revisar queries DB.

---

#### 4. Request Latency p50 (by endpoint)

**Tipo:** Time Series
**Query:** `histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))`

- **Descripción:** Mediana de latencia (experiencia típica del usuario).
- **Valores normales:** < 500 ms.

---

#### 5. Top 10 Slowest Endpoints (p95)

**Tipo:** Table
**Query:** `topk(10, histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)))`

- **Descripción:** Tabla de endpoints más lentos ordenados por p95.
- **Uso:** Identificar cuellos de botella.
- **Acción:** Si p95 > 2s → optimizar endpoint.

---

#### 6. Active HTTP Requests (in-progress)

**Tipo:** Stat
**Query:** `sum(http_requests_in_progress)`

- **Descripción:** Requests activos en este momento.
- **Valores normales:** < 10.
- **Thresholds:**
  - Verde: < 5
  - Amarillo: 5-10
  - Rojo: > 10
- **⚠️ Anomalía:** > 10 → posible request bloqueado.

---

## 🎬 Dashboard: Video Processing Pipeline

**UID:** `youtube-ai-video-processing`
**Tags:** `youtube-ai`, `video-processing`, `pipeline`
**Refresh:** 15 segundos
**Time Range:** Últimas 6 horas

### Objetivo

Monitorear el pipeline completo de procesamiento de videos (descarga → transcripción → resumen).

### Paneles

#### 1. Videos by Status

**Tipo:** Pie Chart
**Query:** `sum by (status) (videos_processed_total)`

- **Descripción:** Distribución de videos por estado.
- **Colores:**
  - Completed: Verde
  - Failed: Rojo
- **Valores normales:** > 90% completed.

---

#### 2. Throughput (videos/hour)

**Tipo:** Stat
**Query:** `sum(rate(videos_processed_total{status="completed"}[1h])) * 3600`

- **Descripción:** Videos completados por hora.
- **Valores normales:** 30-120 videos/hora (depende de duración).
- **Thresholds:**
  - Verde: > 5
  - Amarillo: 1-5
  - Rojo: < 1

---

#### 3. Total Videos Completed

**Tipo:** Stat
**Query:** `sum(videos_processed_total{status="completed"})`

- **Descripción:** Contador total de videos completados exitosamente.

---

#### 4. Processing Duration by Phase (avg)

**Tipo:** Time Series (bars)
**Query:** `avg by (phase) (rate(video_processing_duration_seconds_sum[5m]) / rate(video_processing_duration_seconds_count[5m]))`

- **Descripción:** Duración promedio de cada fase.
- **Fases:**
  - Download
  - Transcription
  - Summary
  - Total
- **Valores normales:**
  - Download: 5-15s
  - Transcription: 60-180s
  - Summary: 5-10s

---

#### 5. Audio Download Duration (p95)

**Tipo:** Time Series
**Query:** `histogram_quantile(0.95, sum(rate(audio_download_duration_seconds_bucket[5m])) by (le))`

- **Descripción:** Percentil 95 de tiempo de descarga de audio.
- **Valores normales:** < 30s.
- **⚠️ Anomalía:** > 60s → problema de red o YouTube throttling.

---

#### 6. Transcription Duration (p95)

**Tipo:** Time Series
**Query:** `histogram_quantile(0.95, sum(rate(transcription_duration_seconds_bucket[5m])) by (le))`

- **Descripción:** Percentil 95 de tiempo de transcripción.
- **Valores normales:** 60-180s (depende de duración del video).
- **⚠️ Anomalía:** > 300s → modelo Whisper lento o CPU saturada.

---

#### 7. Summary Generation Duration (p95)

**Tipo:** Time Series
**Query:** `histogram_quantile(0.95, sum(rate(summary_generation_duration_seconds_bucket[5m])) by (le))`

- **Descripción:** Percentil 95 de tiempo de generación de resúmenes.
- **Valores normales:** < 10s.
- **⚠️ Anomalía:** > 20s → API DeepSeek lenta o rate limit.

---

#### 8. Top Processing Errors (by type)

**Tipo:** Table
**Query:** `topk(10, sum by (error_type) (video_processing_errors_total))`

- **Descripción:** Tabla de errores más frecuentes.
- **Uso:** Identificar patrones de fallo.
- **Acción:** Si `download` es top → revisar yt-dlp.

---

## 🚨 Alertas Configuradas

Las alertas visuales están configuradas mediante **thresholds** (umbrales de color).

### Tabla de Alertas

| Alerta                         | Condición                                                            | Umbral | Acción Visual  | Acción Recomendada                         |
| ------------------------------ | -------------------------------------------------------------------- | ------ | -------------- | ------------------------------------------ |
| **High Error Rate**            | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(...))` | > 5%   | Panel rojo     | Revisar logs de FastAPI                    |
| **High Latency**               | `histogram_quantile(0.95, ...)`                                      | > 2s   | Panel rojo     | Optimizar queries DB o endpoint            |
| **Cache Performance Degraded** | `cache_hit_rate`                                                     | < 50%  | Panel amarillo | Revisar TTL de cache o conexión Redis      |
| **Queue Growing**              | `celery_tasks_active`                                                | > 50   | Panel rojo     | Escalar workers o revisar tasks bloqueados |
| **Low Success Rate**           | `success_rate`                                                       | < 80%  | Panel rojo     | Revisar errores de procesamiento           |

### Procedimiento ante Alerta Roja

1. **Identificar el panel afectado** (color rojo).
2. **Verificar logs estructurados:**
   ```bash
   docker-compose logs --tail=100 fastapi
   ```
3. **Consultar métricas relacionadas** en otros dashboards.
4. **Ejecutar query PromQL directamente** en Prometheus (http://localhost:9090).
5. **Aplicar fix** según el problema identificado.
6. **Validar que el panel vuelva a verde.**

---

## 🛠️ Troubleshooting

### Problema: "No se ven datos en los paneles"

#### Síntomas

- Paneles en blanco o mensaje "No data".

#### Diagnóstico

1. **Verificar que Prometheus esté scrapeando FastAPI:**
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```
   Buscar `job="fastapi"` con estado `UP`.

2. **Verificar que FastAPI expone métricas:**
   ```bash
   curl http://localhost:8000/metrics
   ```
   Debe retornar métricas en formato Prometheus.

3. **Verificar datasource en Grafana:**
   ```bash
   curl -u admin:admin http://localhost:3000/api/datasources
   ```
   Verificar `url: "http://prometheus:9090"`.

#### Solución

- **Si Prometheus no scrapea FastAPI:**
  ```bash
  # Verificar prometheus.yml
  cat prometheus.yml
  # Reiniciar Prometheus
  docker-compose restart prometheus
  ```

- **Si FastAPI no expone métricas:**
  ```bash
  # Verificar que el endpoint /metrics esté habilitado
  # Reiniciar FastAPI
  docker-compose restart fastapi  # (si estuviera en docker)
  ```

---

### Problema: "Panel muestra error en query PromQL"

#### Síntomas

- Panel con mensaje de error "Parse error" o "Invalid query".

#### Diagnóstico

1. Copiar la query del panel.
2. Ejecutarla directamente en Prometheus UI (http://localhost:9090/graph).
3. Verificar mensaje de error.

#### Solución

- **Métrica no existe:**
  - Verificar nombre exacto en http://localhost:8000/metrics.
  - Corregir query en el panel.

- **Label no existe:**
  - Verificar labels disponibles: `{__name__="nombre_metrica"}`.
  - Ajustar query.

---

### Problema: "Dashboards no se cargan al iniciar Grafana"

#### Síntomas

- Grafana inicia pero dashboards no aparecen.

#### Diagnóstico

1. **Verificar logs de Grafana:**
   ```bash
   docker-compose logs grafana | grep -i "provision"
   ```

2. **Verificar montaje de volúmenes:**
   ```bash
   docker inspect iamonitor_grafana | grep -A 10 "Mounts"
   ```

#### Solución

- **Volumen no montado:**
  ```bash
  # Verificar docker-compose.yml, sección grafana:
  volumes:
    - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
  # Reiniciar
  docker-compose down && docker-compose up -d
  ```

- **JSON inválido:**
  ```bash
  # Validar JSON de dashboards
  python3 -m json.tool grafana/dashboards/system-overview.json
  ```

---

### Problema: "Grafana no inicia (health check failed)"

#### Síntomas

- `docker-compose ps` muestra Grafana como `unhealthy`.

#### Diagnóstico

```bash
docker-compose logs grafana --tail=50
```

#### Solución

- **Puerto 3000 ocupado:**
  ```bash
  lsof -i :3000
  # Cambiar puerto en docker-compose.yml
  ports:
    - "3001:3000"
  ```

- **Permisos de volumen:**
  ```bash
  sudo chown -R 472:472 /var/lib/docker/volumes/grafana_data
  ```

---

## ⚙️ Operaciones Avanzadas

### Exportar Dashboard como JSON

Desde la UI de Grafana:

1. Abrir dashboard.
2. Click en **Settings** (⚙️ icono superior derecha).
3. **JSON Model** → **Copy to Clipboard**.
4. Guardar en `grafana/dashboards/<nombre>.json`.

### Crear Dashboard Personalizado

1. Acceder a Grafana → **Dashboards** → **New Dashboard**.
2. Añadir paneles con queries PromQL.
3. Exportar JSON (ver arriba).
4. Guardar en `grafana/dashboards/`.
5. Grafana lo cargará automáticamente en <10 segundos.

### Reload de Dashboards sin Reiniciar

Grafana detecta cambios automáticamente cada 10 segundos (ver `updateIntervalSeconds` en `grafana/provisioning/dashboards/default.yml`).

### Consultar API de Grafana

Listar dashboards:
```bash
curl -u admin:admin http://localhost:3000/api/search?type=dash-db | jq .
```

Obtener JSON de un dashboard:
```bash
curl -u admin:admin http://localhost:3000/api/dashboards/uid/youtube-ai-system-overview | jq .
```

### Backup de Dashboards

```bash
# Backup manual
mkdir -p backups/grafana
curl -u admin:admin http://localhost:3000/api/search?type=dash-db | \
  jq -r '.[].uid' | \
  while read uid; do
    curl -u admin:admin http://localhost:3000/api/dashboards/uid/$uid > backups/grafana/$uid.json
  done
```

---

## 📚 Referencias

- [Prometheus Query Basics](../docs/prometheus-queries.md)
- [Prometheus Operations Guide](../docs/prometheus-operations.md)
- [Grafana Official Docs](https://grafana.com/docs/grafana/latest/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)

---

## 📝 Historial de Versiones

| Versión | Fecha      | Cambios                               |
| ------- | ---------- | ------------------------------------- |
| 1.0     | 15/11/2025 | Versión inicial - Paso 23 del roadmap |

---

**Mantenido por:** Pablo (prodelaya)
**Proyecto:** YouTube AI Summary
**Stack:** Grafana 10.2.0 + Prometheus 2.48.0
