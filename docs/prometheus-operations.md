# Guía de Operaciones: Prometheus & Grafana

**Proyecto:** youtube-AIsummary
**Paso:** 22 - Sistema de Métricas
**Última actualización:** 15/11/2025

---

## 📋 Tabla de Contenidos

1. [Setup Inicial](#setup-inicial)
2. [Gestión de Servicios](#gestión-de-servicios)
3. [Verificación de Salud](#verificación-de-salud)
4. [Configuración de Grafana](#configuración-de-grafana)
5. [Exporters Adicionales](#exporters-adicionales)
6. [Mantenimiento](#mantenimiento)
7. [Troubleshooting](#troubleshooting)
8. [Backup y Restauración](#backup-y-restauración)
9. [Monitorización en Producción](#monitorización-en-producción)

---

## Setup Inicial

### 1. Requisitos Previos

**Software necesario:**
```bash
# Docker y Docker Compose
docker --version  # >= 20.10
docker-compose --version  # >= 1.29

# Python y Poetry
python --version  # >= 3.11
poetry --version  # >= 1.8
```

**Recursos del sistema:**
- **RAM:** 8 GB (mínimo 4 GB libres)
- **CPU:** 2+ cores
- **Disco:** 10 GB libres

### 2. Instalación Básica

**Clonar y preparar el proyecto:**
```bash
cd /home/prodelaya/proyectos/youtube-AIsummary

# Instalar dependencias Python
poetry install

# Verificar prometheus-client
poetry show prometheus-client
```

**Iniciar infraestructura:**
```bash
# Iniciar PostgreSQL, Redis y Prometheus
docker-compose up -d

# Verificar que todos los servicios están corriendo
docker-compose ps
```

**Salida esperada:**
```
NAME                   STATUS    PORTS
iamonitor_postgres     Up        0.0.0.0:5432->5432/tcp
iamonitor_redis        Up        0.0.0.0:6379->6379/tcp
iamonitor_prometheus   Up        0.0.0.0:9090->9090/tcp
```

### 3. Iniciar Aplicación

**Terminal 1 - FastAPI:**
```bash
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Celery Worker:**
```bash
poetry run celery -A src.core.celery_app worker --loglevel=info --queues=video_processing --concurrency=1 --pool=solo
```

**Terminal 3 - Celery Beat (opcional, para tareas programadas):**
```bash
poetry run celery -A src.core.celery_app beat --loglevel=info
```

### 4. Verificar Métricas

**Verificar endpoint de métricas:**
```bash
curl http://localhost:8000/metrics
```

**Salida esperada:**
```
# HELP http_requests_total Total de requests HTTP recibidos
# TYPE http_requests_total counter
http_requests_total{endpoint="/metrics",method="GET",status="200"} 1.0
...
```

**Acceder a Prometheus UI:**
```bash
# Abrir en navegador
http://localhost:9090

# Ejecutar query de prueba
up
```

---

## Gestión de Servicios

### Docker Compose

**Iniciar todos los servicios:**
```bash
docker-compose up -d
```

**Detener todos los servicios:**
```bash
docker-compose down
```

**Reiniciar un servicio específico:**
```bash
docker-compose restart prometheus
```

**Ver logs:**
```bash
# Todos los servicios
docker-compose logs -f

# Servicio específico
docker-compose logs -f prometheus

# Últimas 100 líneas
docker-compose logs --tail=100 prometheus
```

**Eliminar todo (incluyendo volúmenes):**
```bash
# ⚠️ PELIGRO: Borra todos los datos persistidos
docker-compose down -v
```

### Prometheus

**Reload de configuración (sin reiniciar):**
```bash
# Método 1: API
curl -X POST http://localhost:9090/-/reload

# Método 2: Docker
docker-compose exec prometheus kill -HUP 1
```

**Verificar configuración:**
```bash
# Validar prometheus.yml
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

**Verificar reglas de alerting:**
```bash
docker-compose exec prometheus promtool check rules /etc/prometheus/alert_rules.yml
```

### FastAPI

**Modo desarrollo (con auto-reload):**
```bash
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Modo producción (con workers):**
```bash
poetry run gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Background (con supervisord o systemd):**
```bash
# Ver sección "Monitorización en Producción"
```

### Celery

**Worker con configuración personalizada:**
```bash
poetry run celery -A src.core.celery_app worker \
  --loglevel=info \
  --queues=video_processing,scraping \
  --concurrency=2 \
  --pool=solo \
  --max-tasks-per-child=100
```

**Flower (UI de Celery):**
```bash
poetry run celery -A src.core.celery_app flower --port=5555
```

Acceder a: `http://localhost:5555`

**Inspeccionar tareas activas:**
```bash
# Tareas activas
poetry run celery -A src.core.celery_app inspect active

# Tareas programadas
poetry run celery -A src.core.celery_app inspect scheduled

# Estado de workers
poetry run celery -A src.core.celery_app inspect stats
```

**Purgar todas las tareas:**
```bash
# ⚠️ Elimina TODAS las tareas pendientes
poetry run celery -A src.core.celery_app purge
```

---

## Verificación de Salud

### Health Checks

**PostgreSQL:**
```bash
# Desde host
docker-compose exec postgres pg_isready -U iamonitor

# Conectar a BD
docker-compose exec postgres psql -U iamonitor -d iamonitor
```

**Redis:**
```bash
# Ping
docker-compose exec redis redis-cli ping
# Debe retornar: PONG

# Ver info
docker-compose exec redis redis-cli info
```

**Prometheus:**
```bash
# Health endpoint
curl http://localhost:9090/-/healthy
# Debe retornar: Prometheus is Healthy.

# Ready endpoint
curl http://localhost:9090/-/ready
# Debe retornar: Prometheus is Ready.
```

**FastAPI:**
```bash
# Health check (si lo implementas)
curl http://localhost:8000/health

# Metrics endpoint
curl http://localhost:8000/metrics
```

### Monitoring Targets

**Ver estado de targets en Prometheus:**

1. Acceder a: `http://localhost:9090/targets`
2. Verificar que `fastapi` tiene estado `UP`
3. Verificar `Last Scrape` < 30 segundos

**CLI:**
```bash
# Query para verificar targets UP
curl -G 'http://localhost:9090/api/v1/query' --data-urlencode 'query=up'
```

**Salida esperada:**
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {"instance": "fastapi-main", "job": "fastapi"},
        "value": [1699999999, "1"]
      }
    ]
  }
}
```

---

## Configuración de Grafana

### 1. Instalación de Grafana

**Añadir a docker-compose.yml:**
```yaml
  grafana:
    image: grafana/grafana:10.2.0
    container_name: iamonitor_grafana
    restart: unless-stopped

    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false

    ports:
      - "3000:3000"

    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning

    depends_on:
      - prometheus

    networks:
      - iamonitor_network

volumes:
  grafana_data:
```

**Iniciar Grafana:**
```bash
docker-compose up -d grafana
```

### 2. Configurar Data Source

**Acceder a Grafana:**
```
URL: http://localhost:3000
Usuario: admin
Password: admin
```

**Añadir Prometheus como Data Source:**

1. Ir a: **Configuration → Data Sources → Add data source**
2. Seleccionar: **Prometheus**
3. Configurar:
   - **Name:** Prometheus
   - **URL:** `http://prometheus:9090`
   - **Access:** Server (default)
4. Click: **Save & Test**

**Provisioning automático (recomendado):**

Crear `grafana/provisioning/datasources/prometheus.yml`:
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### 3. Importar Dashboards

**Dashboard de ejemplo para FastAPI:**

Crear `grafana/provisioning/dashboards/fastapi.json`:

```json
{
  "dashboard": {
    "title": "FastAPI Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m]))"
          }
        ]
      },
      {
        "title": "Latency p95",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
```

**Importar desde Grafana.com:**

1. Ir a: **Dashboards → Import**
2. Introducir ID de dashboard:
   - **3662** - Prometheus 2.0 Overview
   - **11074** - Node Exporter Full
   - **7589** - PostgreSQL Database
3. Seleccionar data source: **Prometheus**
4. Click: **Import**

### 4. Crear Dashboard Personalizado

**Panel de Video Processing:**

```json
{
  "title": "Video Processing",
  "panels": [
    {
      "title": "Videos Processed/min",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(videos_processed_total[5m])) * 60",
          "legendFormat": "Total"
        },
        {
          "expr": "sum by (status) (rate(videos_processed_total[5m])) * 60",
          "legendFormat": "{{ status }}"
        }
      ]
    },
    {
      "title": "Processing Duration by Phase",
      "type": "graph",
      "targets": [
        {
          "expr": "avg by (phase) (rate(video_processing_duration_seconds_sum[5m]) / rate(video_processing_duration_seconds_count[5m]))",
          "legendFormat": "{{ phase }}"
        }
      ]
    },
    {
      "title": "Active Videos",
      "type": "stat",
      "targets": [
        {
          "expr": "active_video_processing"
        }
      ]
    }
  ]
}
```

---

## Exporters Adicionales

### 1. Node Exporter (Métricas de Sistema)

**Añadir a docker-compose.yml:**
```yaml
  node_exporter:
    image: prom/node-exporter:v1.7.0
    container_name: iamonitor_node_exporter
    restart: unless-stopped

    command:
      - '--path.rootfs=/host'
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'

    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro

    ports:
      - "9100:9100"

    networks:
      - iamonitor_network
```

**Añadir a prometheus.yml:**
```yaml
scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']
        labels:
          service: 'node-exporter'
```

**Reiniciar servicios:**
```bash
docker-compose up -d node_exporter
docker-compose restart prometheus
```

### 2. Postgres Exporter

**Añadir a docker-compose.yml:**
```yaml
  postgres_exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    container_name: iamonitor_postgres_exporter
    restart: unless-stopped

    environment:
      DATA_SOURCE_NAME: "postgresql://iamonitor:iamonitor_dev_password@postgres:5432/iamonitor?sslmode=disable"

    ports:
      - "9187:9187"

    depends_on:
      - postgres

    networks:
      - iamonitor_network
```

**Añadir a prometheus.yml:**
```yaml
scrape_configs:
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']
        labels:
          service: 'postgresql'
          database: 'iamonitor'
```

### 3. Redis Exporter

**Añadir a docker-compose.yml:**
```yaml
  redis_exporter:
    image: oliver006/redis_exporter:v1.55.0
    container_name: iamonitor_redis_exporter
    restart: unless-stopped

    environment:
      REDIS_ADDR: "redis:6379"

    ports:
      - "9121:9121"

    depends_on:
      - redis

    networks:
      - iamonitor_network
```

**Añadir a prometheus.yml:**
```yaml
scrape_configs:
  - job_name: 'redis'
    static_configs:
      - targets: ['redis_exporter:9121']
        labels:
          service: 'redis'
```

### 4. Verificar Exporters

```bash
# Node Exporter
curl http://localhost:9100/metrics | grep "node_"

# Postgres Exporter
curl http://localhost:9187/metrics | grep "pg_"

# Redis Exporter
curl http://localhost:9121/metrics | grep "redis_"
```

---

## Mantenimiento

### 1. Gestión de Retención

**Configurar retención en prometheus:**

```yaml
# En docker-compose.yml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'  # 30 días
    - '--storage.tsdb.retention.size=10GB' # 10 GB
```

**Verificar uso de disco:**
```bash
# Tamaño de datos de Prometheus
docker-compose exec prometheus du -sh /prometheus

# Detalle por directorio
docker-compose exec prometheus du -h /prometheus | sort -h
```

### 2. Limpieza de Datos

**Eliminar series antiguas (compaction):**
```bash
# Prometheus hace compaction automáticamente cada 2 horas
# Forzar compaction (requiere reinicio)
docker-compose restart prometheus
```

**Eliminar series específicas:**
```promql
# Via API (requiere --web.enable-admin-api)
curl -X POST -g 'http://localhost:9090/api/v1/admin/tsdb/delete_series?match[]={job="old_job"}'
```

### 3. Monitorizar Prometheus

**Métricas de Prometheus sobre sí mismo:**

```promql
# Uso de memoria
process_resident_memory_bytes / 1024 / 1024  # MB

# Series temporales activas
prometheus_tsdb_head_series

# Muestras ingeridas/s
rate(prometheus_tsdb_head_samples_appended_total[5m])

# Duración de scraping
scrape_duration_seconds

# Errores de scraping
up == 0
```

**Dashboard recomendado:**
- Grafana Dashboard ID: **3662** (Prometheus 2.0 Overview)

### 4. Logs

**Ver logs de Prometheus:**
```bash
docker-compose logs -f prometheus
```

**Logs importantes a vigilar:**
```
# Errores de scraping
level=error ts=... caller=scrape.go msg="Scrape failed"

# Alta cardinalidad
level=warn ts=... msg="Creating series with label __name__=..."

# Falta de espacio
level=error ts=... msg="compaction failed" err="not enough disk space"
```

---

## Troubleshooting

### Problema 1: Prometheus no puede scrapear FastAPI

**Síntoma:**
Target `fastapi` en estado `DOWN` en http://localhost:9090/targets

**Diagnóstico:**
```bash
# Verificar que FastAPI está corriendo
curl http://localhost:8000/metrics

# Verificar conectividad desde Prometheus
docker-compose exec prometheus wget -O- http://host.docker.internal:8000/metrics
```

**Soluciones:**

1. **FastAPI no está corriendo:**
   ```bash
   poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

2. **Problema de red Docker:**
   ```yaml
   # En docker-compose.yml, añadir extra_hosts
   prometheus:
     extra_hosts:
       - "host.docker.internal:host-gateway"
   ```

3. **Firewall bloqueando puerto 8000:**
   ```bash
   sudo ufw allow 8000/tcp
   ```

### Problema 2: Métricas no aparecen

**Síntoma:**
Query `http_requests_total` retorna "No data"

**Diagnóstico:**
```bash
# Verificar que la métrica existe
curl http://localhost:8000/metrics | grep http_requests_total

# Verificar en Prometheus
curl -G 'http://localhost:9090/api/v1/label/__name__/values' | grep http_requests
```

**Soluciones:**

1. **Métrica no registrada:**
   - Verificar que `metrics` está importado en `src/api/main.py`
   - Verificar que la métrica está definida en `src/core/metrics.py`

2. **Métrica nunca usada:**
   - Las métricas solo aparecen después del primer uso
   - Hacer un request a la API para generar métricas

3. **Prometheus no ha scrapeado todavía:**
   - Esperar 15 segundos (intervalo de scraping)
   - Forzar scrape: Ir a http://localhost:9090/targets y click en target

### Problema 3: Alta Cardinalidad

**Síntoma:**
Prometheus consume mucha RAM o se vuelve lento

**Diagnóstico:**
```promql
# Top 10 métricas con más series
topk(10, count by (__name__)({__name__=~".+"}))

# Series por job
count by (job) ({__name__=~".+"})
```

**Soluciones:**

1. **Eliminar labels con alta cardinalidad:**
   ```python
   # ❌ MAL
   metrics.http_requests_total.labels(
       user_id="uuid-123...",  # Millones de valores
       video_id="uuid-456..."
   ).inc()

   # ✅ BIEN
   metrics.http_requests_total.labels(
       endpoint="/api/videos",  # ~50 valores
       method="GET"             # ~10 valores
   ).inc()
   ```

2. **Usar relabel_config en Prometheus:**
   ```yaml
   scrape_configs:
     - job_name: 'fastapi'
       metric_relabel_configs:
         # Eliminar label problemático
         - source_labels: [__name__]
           regex: 'http_requests_total'
           target_label: 'user_id'
           replacement: ''
   ```

### Problema 4: Disco Lleno

**Síntoma:**
```
level=error msg="compaction failed" err="not enough disk space"
```

**Soluciones:**

1. **Reducir retención:**
   ```yaml
   prometheus:
     command:
       - '--storage.tsdb.retention.time=7d'  # De 15d a 7d
   ```

2. **Limpiar datos viejos:**
   ```bash
   docker-compose down
   # Eliminar volumen
   docker volume rm youtube-aisummary_prometheus_data
   docker-compose up -d
   ```

3. **Aumentar espacio en disco:**
   - Mover volúmenes a disco más grande
   - Limpiar archivos innecesarios

### Problema 5: Grafana No Muestra Datos

**Síntoma:**
Dashboard muestra "No data"

**Diagnóstico:**
```bash
# Verificar data source
curl http://localhost:3000/api/datasources

# Test query directamente en Prometheus
curl -G 'http://localhost:9090/api/v1/query' --data-urlencode 'query=up'
```

**Soluciones:**

1. **Data source mal configurado:**
   - URL debe ser: `http://prometheus:9090` (dentro de Docker)
   - NO usar: `http://localhost:9090`

2. **Rango de tiempo incorrecto:**
   - Cambiar time range a "Last 15 minutes"
   - Verificar que hay datos en ese periodo

3. **Query incorrecta:**
   - Probar query simple primero: `up`
   - Verificar sintaxis PromQL

---

## Backup y Restauración

### 1. Backup de Prometheus

**Crear snapshot:**
```bash
# Requiere --web.enable-admin-api
curl -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot
```

**Salida:**
```json
{"status":"success","data":{"name":"20251115T100000Z-abcd1234"}}
```

**Copiar snapshot:**
```bash
# Snapshot está en /prometheus/snapshots/
docker cp iamonitor_prometheus:/prometheus/snapshots/20251115T100000Z-abcd1234 ./backup/
```

**Backup manual (simple):**
```bash
# Copiar volumen completo
docker run --rm -v youtube-aisummary_prometheus_data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/prometheus-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### 2. Restauración de Prometheus

**Desde snapshot:**
```bash
# Copiar snapshot a volumen
docker cp ./backup/20251115T100000Z-abcd1234 iamonitor_prometheus:/prometheus/snapshots/

# Restaurar
docker-compose exec prometheus promtool tsdb restore /prometheus/restored /prometheus/snapshots/20251115T100000Z-abcd1234
```

**Desde backup manual:**
```bash
# Detener Prometheus
docker-compose down prometheus

# Restaurar volumen
docker run --rm -v youtube-aisummary_prometheus_data:/data -v $(pwd)/backup:/backup alpine tar xzf /backup/prometheus-backup-20251115.tar.gz -C /data

# Reiniciar
docker-compose up -d prometheus
```

### 3. Backup de Grafana

**Backup de dashboards:**
```bash
# Exportar todos los dashboards via API
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:3000/api/search?type=dash-db | jq -r '.[].uri' | while read uri; do
  curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:3000/api/dashboards/$uri > "backup/grafana-$(basename $uri).json"
done
```

**Backup de base de datos Grafana:**
```bash
docker run --rm -v youtube-aisummary_grafana_data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/grafana-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### 4. Automatizar Backups

**Script de backup diario:**

```bash
#!/bin/bash
# backup-metrics.sh

BACKUP_DIR="./backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup Prometheus
docker run --rm \
  -v youtube-aisummary_prometheus_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/$(date +%Y%m%d)/prometheus.tar.gz -C /data .

# Backup Grafana
docker run --rm \
  -v youtube-aisummary_grafana_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/$(date +%Y%m%d)/grafana.tar.gz -C /data .

# Retener solo últimos 30 días
find ./backups -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

**Cronjob:**
```bash
# Ejecutar backup diario a las 2 AM
0 2 * * * /path/to/backup-metrics.sh >> /var/log/backup-metrics.log 2>&1
```

---

## Monitorización en Producción

### 1. Configuración Recomendada

**docker-compose.prod.yml:**

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.48.0
    restart: always

    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=90d'  # Mayor retención
      - '--storage.tsdb.retention.size=50GB'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'  # Para snapshots

    deploy:
      resources:
        limits:
          memory: 2G  # Mayor memoria
        reservations:
          memory: 1G

    volumes:
      - /srv/prometheus/config:/etc/prometheus
      - /srv/prometheus/data:/prometheus

    ports:
      - "127.0.0.1:9090:9090"  # Solo localhost

    networks:
      - monitoring

  grafana:
    image: grafana/grafana:10.2.0
    restart: always

    environment:
      - GF_SERVER_ROOT_URL=https://metrics.example.com
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_SMTP_ENABLED=true
      - GF_SMTP_HOST=smtp.gmail.com:587

    volumes:
      - /srv/grafana/data:/var/lib/grafana
      - /srv/grafana/provisioning:/etc/grafana/provisioning

    ports:
      - "127.0.0.1:3000:3000"

    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### 2. Seguridad

**Habilitar autenticación en Prometheus:**

Usar reverse proxy (nginx) con basic auth:

```nginx
# /etc/nginx/sites-available/prometheus
server {
    listen 443 ssl;
    server_name prometheus.example.com;

    ssl_certificate /etc/letsencrypt/live/prometheus.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/prometheus.example.com/privkey.pem;

    auth_basic "Prometheus";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://localhost:9090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Crear usuario:**
```bash
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

### 3. Alertmanager

**Añadir Alertmanager:**

```yaml
# docker-compose.prod.yml
  alertmanager:
    image: prom/alertmanager:v0.26.0
    restart: always

    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'

    volumes:
      - /srv/alertmanager/config:/etc/alertmanager
      - /srv/alertmanager/data:/alertmanager

    ports:
      - "127.0.0.1:9093:9093"

    networks:
      - monitoring
```

**Configurar alertmanager.yml:**

```yaml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'your_password'

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-email'

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'devops@example.com'
        headers:
          Subject: '[ALERT] {{ .GroupLabels.alertname }}'

  - name: 'slack-critical'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts-critical'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
```

**Añadir a prometheus.yml:**
```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - 'alert_rules.yml'
```

### 4. Monitoring de Logs

**Loki + Promtail (opcional):**

Para correlacionar métricas con logs:

```yaml
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - /srv/loki/config:/etc/loki
      - /srv/loki/data:/loki

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log:ro
      - /srv/promtail/config:/etc/promtail
```

---

## Checklist de Producción

Antes de desplegar a producción:

### Prometheus
- [ ] Configurar retención adecuada (30-90 días)
- [ ] Habilitar autenticación (reverse proxy)
- [ ] Configurar backup automático
- [ ] Limitar recursos (memoria, CPU)
- [ ] Configurar alerting (Alertmanager)
- [ ] Verificar disco suficiente (>50GB)
- [ ] Habilitar HTTPS

### Grafana
- [ ] Cambiar password admin por defecto
- [ ] Configurar SMTP para alertas
- [ ] Provisionar dashboards automáticamente
- [ ] Configurar autenticación (LDAP/OAuth)
- [ ] Habilitar HTTPS
- [ ] Backup de dashboards

### Aplicación
- [ ] Revisar cardinalidad de métricas
- [ ] Asegurar que endpoint /metrics NO está expuesto públicamente
- [ ] Configurar rate limiting
- [ ] Implementar health checks
- [ ] Monitorizar logs (Loki)

### Infraestructura
- [ ] Node Exporter instalado
- [ ] Postgres Exporter configurado
- [ ] Redis Exporter configurado
- [ ] Monitorización de disco
- [ ] Monitorización de red
- [ ] Alertas configuradas

---

## Recursos Adicionales

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [PromQL Guide](prometheus-queries.md)
- [Development Guide](prometheus-guide.md)

---

**Fin de la Guía de Operaciones**
