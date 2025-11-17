# ADR-016: Rate Limiting para Protección contra Abuso

**Fecha**: 2025-11-17
**Estado**: ✅ Implementado
**Paso**: 23.5 - Seguridad Crítica (Día 3)
**Decisor**: Sistema (hardening P1)

---

## Contexto

Después de implementar autenticación JWT (ADR-014) y mitigación de prompt injection (ADR-015), se identificó la necesidad de proteger contra:

1. **Brute-force attacks**: Intentos masivos de adivinar passwords en `/auth/login`
2. **Resource exhaustion**: Abuso del endpoint `/process` (costoso en CPU y $$$)
3. **DoS (Denial of Service)**: Flooding de requests para saturar el servidor
4. **API cost explosion**: Consumo excesivo de DeepSeek API

Sin rate limiting, un atacante puede:
- Intentar 1000s de passwords en `/login` (brute-force)
- Procesar 100s de videos simultáneamente (costos altos)
- Saturar el servidor con requests (DoS)

---

## Decisión

Implementar **rate limiting por endpoint** usando **SlowAPI** (wrapper de slowapi para FastAPI):

### Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│              RATE LIMITING POR ENDPOINT                  │
└─────────────────────────────────────────────────────────┘

Request → FastAPI → SlowAPI Middleware → Endpoint
                          │
                          ├─> Identificar IP (get_remote_address)
                          ├─> Consultar contador en Redis
                          ├─> Incrementar contador
                          └─> Verificar límite
                               │
                               ├─> Dentro del límite → Permitir
                               └─> Excede límite → 429 Too Many Requests
```

### Límites por criticidad:

| Endpoint | Límite | Razón |
|----------|--------|-------|
| `POST /auth/login` | **5 req/min** | Anti brute-force de passwords |
| `POST /videos` | **10 req/min** | Prevenir spam de creación |
| `POST /videos/{id}/process` | **3 req/min** | Operación costosa (Whisper + DeepSeek) |
| Global (todos) | **100 req/min** | Protección general contra DoS |

### Estrategia: Fixed Window

```
Minuto 1: [R R R R R] ✅ (5 requests OK)
Minuto 2: [R R R R R R] ❌ (6th request → 429)
Minuto 3: [R R R] ✅ (contador reseteado)
```

---

## Implementación

### 1. Configuración global

```python
# src/api/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,  # Identificar por IP
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri=settings.REDIS_URL,  # Persistencia en Redis
    strategy="fixed-window",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### 2. Rate limiting por endpoint

```python
# src/api/auth/routes.py
@router.post("/login")
@limiter.limit("5/minute")  # ← RATE LIMIT
def login(
    request: Request,  # ← Requerido por SlowAPI
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    ...
```

```python
# src/api/routes/videos.py
@router.post("/{video_id}/process")
@limiter.limit("3/minute")  # ← Más restrictivo (operación costosa)
def process_video(
    request: Request,
    video_id: UUID,
    ...
):
    ...
```

### 3. Handler de errores personalizado

```python
# src/api/main.py
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Respuesta 429 con formato consistente."""
    error = ErrorResponse(
        detail="Too many requests. Please try again later.",
        error_code="RATE_LIMIT_EXCEEDED",
        metadata={
            "path": str(request.url),
            "retry_after": "60 seconds",
        },
    )
    return JSONResponse(
        status_code=429,
        content=error.model_dump(),
        headers={"Retry-After": "60"},
    )
```

### 4. Configuración (.env)

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URI=  # Si vacío, usa REDIS_URL
```

---

## Consecuencias

### ✅ Positivas

1. **Protección automática**: Sin cambios en lógica de negocio
2. **Persistencia en Redis**: Límites compartidos entre workers
3. **Escalable**: Redis soporta millones de keys (IPs)
4. **Configurable**: Límites ajustables por endpoint
5. **Estándar HTTP**: Usa status 429 y header `Retry-After`
6. **Bajo overhead**: Redis GET/INCR son operaciones O(1)

### ⚠️ Consideraciones

1. **Falsos positivos**: Usuarios detrás de NAT comparten IP → comparten límite
2. **Evasión simple**: Atacante puede cambiar IP (VPN, proxies)
3. **Redis SPOF**: Si Redis cae, rate limiting no funciona (fail-open)
4. **Ventana fija**: Permite "burst" al inicio de cada minuto

### 🔒 Seguridad implementada

- **Anti brute-force**: Login limitado a 5 intentos/min
- **Anti DoS**: Límite global de 100 req/min por IP
- **Cost control**: Process limitado a 3/min (protege DeepSeek API costs)
- **Logging**: SlowAPI loggea todos los rate limits excedidos

---

## Alternativas consideradas

### Opción A: Token Bucket (rechazada)
- ✅ Más flexible que fixed window
- ✅ Permite bursts controlados
- ❌ Más complejo de implementar
- ❌ Mayor uso de memoria en Redis

### Opción B: Sliding Window (rechazada)
- ✅ Más justo que fixed window
- ✅ Evita "burst attack" al cambio de minuto
- ❌ Requiere más operaciones en Redis (ZRANGE)
- ❌ Mayor latencia (~5ms vs ~1ms)

### Opción C: NGINX rate limiting (rechazada)
- ✅ Muy eficiente (nivel TCP)
- ✅ No consume recursos de Python
- ❌ Configuración fuera de aplicación
- ❌ Difícil ajustar límites por endpoint
- ❌ No usa Redis (estado no compartido)

### Opción D: Cloudflare Rate Limiting (rechazada)
- ✅ Protección DDoS nivel global
- ✅ Sin carga en servidor
- ❌ Requiere proxy de Cloudflare
- ❌ Costo adicional ($$$)
- ❌ Menos control granular

---

## Evasión y contramedidas

### Ataques posibles:

1. **Distributed attack** (múltiples IPs):
   ```
   Contramedida: Limitar a nivel de usuario autenticado
   (Implementación futura si es necesario)
   ```

2. **Proxy rotation**:
   ```
   Contramedida: Detectar patrones sospechosos (ML)
   + Captcha después de X intentos fallidos
   ```

3. **Cambio de minuto** (burst al inicio de ventana):
   ```
   Contramedida: Cambiar a sliding window
   (Solo si se detecta abuso en producción)
   ```

---

## Monitoring y alertas

### Métricas clave

```python
# Prometheus metrics (a implementar)
rate_limit_exceeded_total{endpoint="/auth/login"}  # Total bloqueados
rate_limit_requests_total{endpoint="/auth/login"}   # Total requests

# Alerta si muchos bloques
ALERT RateLimitAbuse
  IF rate(rate_limit_exceeded_total[5m]) > 10
  FOR 5m
  LABELS { severity="warning" }
  ANNOTATIONS {
    summary="Posible abuso en {{ $labels.endpoint }}"
  }
```

### Logs

```bash
# SlowAPI loggea automáticamente
WARNING slowapi:extension.py:510 ratelimit 5 per 1 minute (192.168.1.100)
  exceeded at endpoint: /api/v1/auth/login

# Buscar ataques
grep "ratelimit.*exceeded" logs/app.log | awk '{print $NF}' | sort | uniq -c
```

---

## Testing

### Test 1: Permite requests dentro del límite
```python
def test_login_rate_limit_allows_within_limit():
    for i in range(4):  # Debajo del límite de 5
        response = client.post("/api/v1/auth/login", ...)
        assert response.status_code in [200, 401]
```

### Test 2: Bloquea requests que exceden límite
```python
def test_login_rate_limit_blocks_over_limit():
    for i in range(6):  # Excede límite de 5
        response = client.post("/api/v1/auth/login", ...)

    assert 429 in status_codes
```

### Test 3: Formato de error correcto
```python
def test_rate_limit_error_format():
    # ... forzar rate limit ...
    response = client.post("/api/v1/auth/login", ...)

    assert response.status_code == 429
    assert "RATE_LIMIT_EXCEEDED" in response.json()["error_code"]
```

---

## Ajuste de límites en producción

### Proceso de ajuste:

```bash
# 1. Analizar métricas de uso real
SELECT
  endpoint,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY requests_per_minute) as p95,
  percentile_cont(0.99) WITHIN GROUP (ORDER BY requests_per_minute) as p99
FROM request_metrics
GROUP BY endpoint;

# 2. Ajustar límites
# Si p99 < límite actual → el límite es demasiado permisivo
# Si p95 > límite actual → usuarios legítimos siendo bloqueados

# 3. Actualizar configuración
# Modificar decoradores @limiter.limit("X/minute")

# 4. Desplegar sin downtime
# (Rate limiting no afecta lógica de negocio)
```

### Límites recomendados por escenario:

| Escenario | Login | Create | Process |
|-----------|-------|--------|---------|
| **Dev/Testing** | 20/min | 50/min | 10/min |
| **Staging** | 10/min | 20/min | 5/min |
| **Producción** | 5/min | 10/min | 3/min |
| **Alto tráfico** | 10/min | 20/min | 5/min |

---

## Desactivar temporalmente

```bash
# En emergencia (si rate limiting causa problemas)
# Opción 1: Desactivar completamente
export RATE_LIMIT_ENABLED=false

# Opción 2: Aumentar límites temporalmente
# Modificar código y redeploy (no recomendado en emergencia)

# Opción 3: Whitelist de IPs (a implementar)
# redis-cli SADD rate_limit:whitelist 192.168.1.100
```

---

## Referencias

- [SlowAPI Documentation](https://slowapi.readthedocs.io/)
- [OWASP Rate Limiting Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)
- [RFC 6585: Additional HTTP Status Codes (429)](https://datatracker.ietf.org/doc/html/rfc6585#section-4)
- [Redis Rate Limiting Patterns](https://redis.io/glossary/rate-limiting/)

---

## Historial

- **2025-11-17**: Implementación inicial (Paso 23.5 - Día 3)
- **Estado actual**: ✅ En producción, protegiendo activamente
