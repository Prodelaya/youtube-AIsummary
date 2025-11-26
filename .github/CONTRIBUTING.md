# Guía de Contribución

Gracias por considerar contribuir a **YouTube IA Summary**. Este documento proporciona las pautas y mejores prácticas para el desarrollo.

---

## 🚀 Configuración del Entorno Local

### Prerrequisitos

- Python 3.11+
- Poetry (gestor de dependencias)
- Docker y Docker Compose
- Git

### Instalación

```bash
# 1. Fork y clonar el repositorio
git clone https://github.com/TU-USUARIO/youtube-AIsummary.git
cd youtube-AIsummary

# 2. Instalar dependencias con Poetry
poetry install

# 3. Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores reales

# 4. Levantar servicios (PostgreSQL, Redis, etc.)
docker-compose up -d

# 5. Ejecutar migraciones
poetry run alembic upgrade head

# 6. Verificar que todo funciona
poetry run pytest
```

---

## 📝 Estándares de Código

Este proyecto sigue **Clean Architecture** y **PEP 8** con herramientas automatizadas.

### Pre-commit Checks

Antes de hacer commit, **ejecuta estos comandos localmente**:

```bash
# 1. Formateo de código (Black)
poetry run black src/ tests/

# 2. Linting (Ruff)
poetry run ruff check src/ tests/ --fix

# 3. Type checking (Mypy)
poetry run mypy src/

# 4. Tests completos
poetry run pytest
```

**Importante:** Todos estos checks se ejecutan automáticamente en CI. Si fallan localmente, también fallarán en GitHub Actions.

---

## 🧪 Tests

### Estructura de Tests

```
tests/
├── unit/              # Tests unitarios (lógica de negocio)
├── integration/       # Tests de integración (servicios + DB)
├── security/          # Tests de seguridad (auth, injection, etc.)
└── conftest.py        # Fixtures compartidos
```

### Ejecutar Tests

```bash
# Todos los tests
poetry run pytest

# Solo tests unitarios
poetry run pytest tests/unit/

# Solo tests de seguridad
poetry run pytest tests/security/

# Con coverage detallado
poetry run pytest --cov=src --cov-report=html
```

### Coverage Mínimo

- **Coverage general:** ≥80%
- **Módulos de seguridad:** ≥90%

---

## 📏 Conventional Commits

Seguimos el estándar de **Conventional Commits** para mensajes de commit claros y semánticos.

### Formato

```
<tipo>(<scope>): <descripción corta>

<cuerpo opcional>

<footer opcional>
```

### Tipos Permitidos

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `feat` | Nueva funcionalidad | `feat(api): add endpoint for video summaries` |
| `fix` | Corrección de bug | `fix(auth): resolve JWT token expiration issue` |
| `test` | Añadir/modificar tests | `test(security): add prompt injection tests` |
| `docs` | Documentación | `docs: update architecture diagram` |
| `refactor` | Refactorización sin cambio funcional | `refactor(services): simplify video processing logic` |
| `perf` | Mejora de rendimiento | `perf(db): optimize query for large datasets` |
| `style` | Cambios de formato (sin lógica) | `style: apply black formatting` |
| `chore` | Tareas de mantenimiento | `chore: update dependencies` |
| `ci` | Cambios en CI/CD | `ci: add security workflow` |

### Ejemplos

```bash
# Nueva funcionalidad
git commit -m "feat(summarizer): implement multi-language support"

# Corrección de bug
git commit -m "fix(celery): resolve worker timeout on long videos"

# Tests
git commit -m "test(api): add integration tests for auth endpoints"

# Documentación
git commit -m "docs: add deployment guide (step 25)"
```

---

## 🔀 Workflow de Contribución

### 1. Crear Rama de Feature

```bash
# Desde main actualizado
git checkout main
git pull origin main

# Crear rama descriptiva
git checkout -b feature/add-youtube-playlist-support
# o
git checkout -b fix/celery-worker-crash
```

### 2. Desarrollar con Tests

- Escribe código siguiendo Clean Architecture
- Añade tests para nueva funcionalidad
- Mantén coverage ≥80%

### 3. Pre-commit Validation

```bash
# Formateo + Linting + Type checking
poetry run black src/ tests/
poetry run ruff check src/ tests/ --fix
poetry run mypy src/

# Tests
poetry run pytest
```

### 4. Commit y Push

```bash
git add .
git commit -m "feat(playlist): add support for YouTube playlists"
git push origin feature/add-youtube-playlist-support
```

### 5. Abrir Pull Request

- Ir a GitHub y abrir PR desde tu rama a `main`
- **Esperar a que pasen los 3 workflows de CI:**
  - ✅ Tests (coverage ≥80%)
  - ✅ Code Quality (black, ruff, mypy)
  - ✅ Security (security tests + audit)

### 6. Code Review

- Responder a comentarios del reviewer
- Hacer cambios solicitados
- Push de commits adicionales (se re-ejecuta CI automáticamente)

### 7. Merge

- Una vez aprobado y CI verde: **Squash & Merge**

---

## ✅ Pull Request Checklist

Antes de abrir un PR, verifica:

- [ ] Tests pasan localmente (`pytest`)
- [ ] Coverage ≥80% en código nuevo
- [ ] Código formateado con Black (`black --check .`)
- [ ] Sin errores de Ruff (`ruff check src/ tests/`)
- [ ] Sin errores de Mypy (`mypy src/`)
- [ ] Type hints en funciones públicas
- [ ] Documentación actualizada (si aplica)
- [ ] Conventional Commits en todos los commits
- [ ] `.env.example` actualizado si hay nuevas variables

---

## 🔒 Seguridad

### Reportar Vulnerabilidades

Si encuentras una vulnerabilidad de seguridad:

1. **NO** abrir un issue público
2. Contactar: `security@prodelaya.dev` (o DM en GitHub)
3. Incluir detalles técnicos y pasos de reproducción
4. Esperar confirmación antes de public disclosure

### Tests de Seguridad

El proyecto incluye tests automatizados para:

- JWT authentication & authorization
- Prompt injection mitigation
- Rate limiting
- Input sanitization
- Output validation
- SQL injection prevention
- XSS prevention

---

## 🧱 Arquitectura del Proyecto

Seguimos **Clean Architecture** con separación en capas:

```
src/
├── api/              # Endpoints FastAPI (controllers)
├── core/             # Config, DB, Celery setup
├── models/           # ORM models (SQLAlchemy)
├── repositories/     # Data access layer
├── services/         # Business logic
├── tasks/            # Celery async tasks
└── utils/            # Shared utilities

tests/
├── unit/             # Unit tests (mocked dependencies)
├── integration/      # Integration tests (real DB/Redis)
└── security/         # Security-specific tests
```

**Reglas de Dependencias:**

- `api` → `services` → `repositories` → `models`
- Nunca al revés (no circular dependencies)
- Tests pueden importar cualquier capa

---

## 📚 Recursos Útiles

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

## 📞 Soporte

- **Issues:** [GitHub Issues](https://github.com/prodelaya/youtube-AIsummary/issues)
- **Discusiones:** [GitHub Discussions](https://github.com/prodelaya/youtube-AIsummary/discussions)
- **Contacto:** proyectos.delaya@gmail.com

---

**¡Gracias por contribuir! 🚀**
