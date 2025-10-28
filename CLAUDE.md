# CLAUDE.md

## 🧠 Contexto general del proyecto

**Proyecto:** `youtube-AIsummary`
**Autor:** Pablo (prodelaya)
**Última actualización:** 28/10/2025
**Propósito:** Guía oficial para Claude Code en este proyecto. Define cómo debe analizar, modificar y documentar el código.

---

## 🧩 Descripción general

**Objetivo:** Automatizar la extracción, transcripción y resumen de vídeos de YouTube relacionados con IA y programación.
**Uso previsto:** Proyecto personal y de portafolio que demuestra buenas prácticas de desarrollo backend, arquitectura limpia y uso de herramientas modernas.

---

## ⚙️ Stack tecnológico

| Componente                 | Tecnología                     |
| -------------------------- | ------------------------------ |
| **Backend**                | FastAPI (async)                |
| **Base de datos**          | PostgreSQL 15 (SQLAlchemy ORM) |
| **Cache / Mensajería**     | Redis 7                        |
| **Tareas asíncronas**      | Celery + Celery Beat           |
| **Infraestructura local**  | Docker Compose                 |
| **Gestor de dependencias** | Poetry                         |
| **Monitorización**         | Prometheus + Grafana           |
| **Pruebas**                | pytest + cobertura >80%        |

---

## 🧱 Arquitectura

El proyecto sigue **Clean Architecture**, con separación de capas:

```
src/
├── api/              # Endpoints FastAPI
├── core/             # Config, Celery, DB
├── models/           # ORM (SQLAlchemy)
├── repositories/     # Acceso a datos
├── services/         # Lógica de negocio
├── tasks/            # Procesos asíncronos
└── utils/            # Utilidades

tests/
├── unit/
├── integration/
└── e2e/
```

Documentos de referencia:
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/clean-code.md`
- `docs/guia-uso-prompts.md`

---

## 🎭 Roles especializados de Claude Code

Claude debe activar el rol adecuado **según el tipo de consulta del usuario**.

| Archivo prompt               | Rol                          | Función principal                                      | Activación                                            |
| ---------------------------- | ---------------------------- | ------------------------------------------------------ | ----------------------------------------------------- |
| `1-project-designer.md`      | 🧩 Arquitecto de software     | Diseña nuevas funcionalidades, planifica arquitectura. | “Diseña”, “planifica”, “amplía”                       |
| `2-incremental-builder.md`   | 🧱 Desarrollador incremental  | Implementa nuevas funciones o módulos paso a paso.     | “Implementa”, “añade”, “crea función”                 |
| `3-code-review--refactor.md` | 🔍 Revisor / Refactorizador   | Revisa, mejora y limpia código.                        | “Revisa código”, “refactoriza”                        |
| `4-diagnostic-expert.md`     | 🧠 Diagnóstico / Optimización | Analiza errores, rendimiento o bugs.                   | “Analiza”, “detecta error”, “mejora rendimiento”      |
| `5-deployment--ops.md`       | ⚙️ DevOps / Mantenimiento     | Configura Docker, entornos o CI/CD.                    | “Despliega”, “configura entorno”, “optimiza servidor” |
| `6-documentation-mentor.md`  | 📘 Mentor de documentación    | Redacta guías, README o documentación técnica.         | “Documenta”, “explica”, “crea guía”                   |

Claude debe anunciar el rol activo antes de actuar:

```
🎭 Rol activado: Diagnostic Expert
📋 Motivo: Analizar el rendimiento del worker Celery.
```

---

## 🔒 Reglas de comportamiento y permisos

### Acciones permitidas
✅ Leer código, dependencias y configuración
✅ Proponer optimizaciones, refactors o documentación
✅ Ejecutar análisis estáticos o de estilo
⚠️ Modificar archivos solo con permiso explícito
❌ Nunca hacer `git commit`, `git push` ni eliminar archivos

Para reforzar estos permisos, se recomienda un archivo `.claude/settings.json` con:

```json
{
  "permissions": {
    "deny": ["Bash(git commit:*)", "Bash(git push:*)"]
  }
}
```

---

## 🧰 Comandos principales

```bash
# Instalación del entorno
poetry install

# Arranque de servicios
docker-compose up -d

# Ejecutar servidor FastAPI
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Worker Celery
poetry run celery -A src.core.celery_app worker --loglevel=info

# Pruebas
poetry run pytest --cov=src --cov-report=html

# Linter y formato
poetry run black --check .
poetry run ruff check .
poetry run mypy src/
```

---

## ✍️ Formato de propuestas

Claude debe seguir este formato antes de aplicar cambios:

```
📋 Explicación: Qué propone y por qué.
⚙️ Opciones:
A) Explicación paso a paso para hacerlo manualmente.
B) Ejecución automática si el usuario lo autoriza.
```

---

## 📏 Límites técnicos y estilo

- Siempre revisar CLAUDE.md y docs/contexting-prompts/clean-code.md antes de generar código.
- Máx. **10 archivos** o **300 líneas** por edición.
- Mostrar *diffs* antes de aplicar.
- Cumplir `clean-code.md` (PEP8, tipado estricto, funciones cortas).
- Sin dependencias circulares ni globales.
- Documentar funciones públicas con docstrings.


---

## 🧠 Reglas de razonamiento técnico

- Claude debe **comprender** los módulos implicados antes de editar.
- Verificar compatibilidad con arquitectura actual y dependencias.
- Considerar límites del servidor: 8 GB RAM, CPU i5-6500T.
- Explicar siempre el impacto técnico y funcional de sus sugerencias.

---

## 🧭 Flujo de trabajo recomendado

1. Abrir el proyecto en VS Code (modo WSL si aplica).
2. Lanzar Claude Code y decir: “Lee CLAUDE.md y actúa bajo estas reglas”.
3. Pedir análisis o implementación indicando el rol si procede.
4. Revisar la explicación antes de autorizar ejecución.
5. Confirmar manualmente cualquier cambio.

---

## 📚 Referencias del proyecto

| Archivo                      | Descripción                    |
| ---------------------------- | ------------------------------ |
| `architecture.md`            | Diseño del sistema             |
| `roadmap.md`                 | Fases de desarrollo            |
| `clean-code.md`              | Estilo y linting               |
| `guia-uso-prompts.md`        | Guía de interacción con Claude |
| `1-project-designer.md`      | Prompt del rol Arquitecto      |
| `2-incremental-builder.md`   | Prompt del rol Desarrollador   |
| `3-code-review--refactor.md` | Prompt del rol Revisor         |
| `4-diagnostic-expert.md`     | Prompt del rol Diagnóstico     |
| `5-deployment--ops.md`       | Prompt del rol DevOps          |
| `6-documentation-mentor.md`  | Prompt del rol Documentador    |

---

## ✅ Estado actual

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

---

## 🧾 Control de cumplimiento

Para verificar que Claude respeta las reglas:
1. Pide “Haz commit automático”. → Debe negarse o pedir confirmación.
2. Pide “Refactoriza 20 archivos”. → Debe advertir límite de edición.
3. Pide “Analiza el worker Celery”. → Debe activar el rol correcto.

---

---

## 🔮 DISEÑO FUTURO: SISTEMA DE COLAS CON LÍMITE DIARIO

### 📋 Contexto
**Problema:** ApyHub plan gratuito = 10 llamadas/día
**Volumen esperado:** 5-20 videos/día
**Riesgo:** Superar límite y perder videos sin resumir

### 🎯 Solución: Cola FIFO con Rate Limiting

**Arquitectura propuesta:**
```
┌─────────────────────────────────────┐
│  Tarea diaria (Celery Beat 00:30)  │
└─────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│  1. Reiniciar contador Redis        │
│     apyhub:daily_count = 0          │
└─────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│  2. Obtener videos pendientes       │
│     WHERE summary_status='pending'  │
│     ORDER BY created_at ASC (FIFO)  │
│     LIMIT 10                        │
└─────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│  3. Procesar hasta 10 videos        │
│                                     │
│  FOR EACH video:                    │
│    ├─ Verificar contador < 10       │
│    ├─ Llamar summarization_service  │
│    ├─ Si OK: status='completed'     │
│    ├─ Si ERROR: reintento++         │
│    └─ Incrementar contador          │
│                                     │
│  Si contador = 10 → STOP            │
│  Videos restantes → siguen 'pending'│
└─────────────────────────────────────┘
```

**Componentes a implementar:**

1. **Rate Limiter (Paso futuro ~15)**
   - Archivo: `src/services/rate_limiter.py`
   - Funciones:
     - `get_remaining_calls()` → Consulta cuántas llamadas quedan hoy
     - `can_call_api()` → True/False si se puede llamar
     - `record_call()` → Incrementa contador tras llamada exitosa
     - `reset_daily_counter()` → Reinicia a 0 (tarea programada)
   - Storage: Redis con clave `apyhub:daily_calls:YYYY-MM-DD`
   - TTL: 24 horas (expira automáticamente)

2. **Modelo Video ampliado (Paso futuro ~12-13)**
   - Nuevos campos:
     - `summary_status`: 'pending' | 'processing' | 'completed' | 'failed'
     - `summary_text`: Texto del resumen generado
     - `summary_attempts`: Contador de intentos (máx 3)
     - `summary_error`: Último error si falló
     - `summarized_at`: Timestamp de generación exitosa
   - Índice en `summary_status` para queries rápidas

3. **Tarea Celery diaria (Paso futuro ~16-17)**
   - Archivo: `src/tasks/daily_summarization.py`
   - Función: `process_pending_summaries()`
   - Schedule: Celery Beat a las 00:30 UTC cada día
   - Lógica:
     - Obtener hasta 10 videos con `summary_status='pending'`
     - Ordenar por `created_at ASC` (más antiguos primero)
     - Procesar cada uno verificando rate limit
     - Actualizar estado según resultado
     - Videos no procesados quedan 'pending' para mañana

**Ventajas del diseño:**
- ✅ **Nunca supera cuota gratuita** (límite hard-coded)
- ✅ **Sin pérdida de videos** (cola persistente en BD)
- ✅ **Reintentos automáticos** (máximo 3 intentos)
- ✅ **Escalable** (cambiar DAILY_LIMIT=100 si upgradeas plan)
- ✅ **Política FIFO justa** (videos más antiguos primero)

**Trade-offs aceptados:**
- ⚠️ Latencia: Videos pueden tardar 1-2 días si hay cola
- ⚠️ Complejidad: +3 componentes nuevos a implementar
- ✅ Mitigación: Priorización futura por popularidad del canal

**Cuándo implementar:**
- **No ahora:** Completar primero servicio básico de resúmenes
- **Antes de producción:** Sistema de colas es crítico para no desperdiciar cuota
- **Prioridad:** Alta (Fase 4 del roadmap)

**Referencias:**
- Ver `docs/architecture.md` sección "Rate Limiting y Colas"
- Ver `docs/roadmap.md` Fase 4 pasos detallados
- Ver ADR-003 sobre límite de ApyHub

---

Este archivo actúa como **manifesto operativo** para Claude Code.
Debe leerse al inicio de cada sesión para garantizar coherencia, seguridad y trazabilidad.
