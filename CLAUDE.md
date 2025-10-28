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

| Archivo                      | Rol                          | Función principal                                          | Palabras de activación                                |
| ---------------------------- | ---------------------------- | ---------------------------------------------------------- | ----------------------------------------------------- |
| `1-project-designer.md`      | 🧩 Arquitecto de software     | Diseña nuevas funcionalidades y planifica la arquitectura. | “diseña”, “planifica”, “amplía”                       |
| `2-incremental-builder.md`   | 🧱 Desarrollador incremental  | Implementa nuevas funciones o módulos paso a paso.         | “implementa”, “añade”, “crea función”                 |
| `3-code-review--refactor.md` | 🔍 Revisor / Refactorizador   | Revisa, mejora y limpia código.                            | “revisa código”, “refactoriza”                        |
| `4-diagnostic-expert.md`     | 🧠 Diagnóstico / Optimización | Analiza errores, rendimiento o bugs.                       | “analiza”, “detecta error”, “mejora rendimiento”      |
| `5-deployment--ops.md`       | ⚙️ DevOps / Mantenimiento     | Configura Docker, entornos o CI/CD.                        | “despliega”, “configura entorno”, “optimiza servidor” |
| `6-documentation-mentor.md`  | 📘 Mentor de documentación    | Redacta guías, README o documentación técnica.             | “documenta”, “explica”, “crea guía”                   |

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
- Cuando sugieras textos de commits sigue las convenciones declaradas en docs/     contexting-prompts/commit-guide.md


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
| `commit-guide.md`            | Guía de commits                |
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

Este archivo actúa como **manifesto operativo** para Claude Code.
Debe leerse al inicio de cada sesión para garantizar coherencia, seguridad y trazabilidad.
