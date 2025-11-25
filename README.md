# IA Monitor - Agregador Inteligente de Contenido

> Agregador automático que transcribe, resume y clasifica contenidos sobre IA en desarrollo software

<!-- Badges de CI/CD -->
[![Tests](https://github.com/prodelaya/youtube-AIsummary/actions/workflows/test.yml/badge.svg)](https://github.com/prodelaya/youtube-AIsummary/actions/workflows/test.yml)
[![Code Quality](https://github.com/prodelaya/youtube-AIsummary/actions/workflows/lint.yml/badge.svg)](https://github.com/prodelaya/youtube-AIsummary/actions/workflows/lint.yml)
[![Security](https://github.com/prodelaya/youtube-AIsummary/actions/workflows/security.yml/badge.svg)](https://github.com/prodelaya/youtube-AIsummary/actions/workflows/security.yml)

<!-- Badges de Proyecto -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/Status-En%20Desarrollo-orange.svg)]()

---

## 📊 Estado del Proyecto

| Métrica | Valor | Descripción |
|---------|-------|-------------|
| **Tests** | 177+ | Suite completa de tests (unit, integration, security) |
| **Coverage** | >80% | Cobertura de código validada en CI |
| **Security Tests** | 33/35 | Tests de seguridad (JWT, Rate Limiting, Prompt Injection) |
| **CI/CD** | ✅ Automatizado | GitHub Actions (tests, lint, security) |
| **Deployment** | 🚧 En progreso | Paso 26-27 (Docker + Deploy) |

---

## QuickStart

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/youtube-AIsummary.git
cd youtube-AIsummary

# Copiar variables de entorno
cp .env.example .env
# Editar .env con tus valores reales

# (Próximos pasos: Poetry, Docker, etc. - Por implementar)
```

---

## Objetivo

**Doble propósito:**
1. **Utilidad real:** Mantenerse informado sobre novedades en IA
2. **Portfolio profesional:** Demostrar backend Python moderno con IA funcional

---

## Stack Tecnológico (Planificado)

- **Backend:** FastAPI (async)
- **Database:** PostgreSQL
- **Cache:** Redis
- **Workers:** Celery
- **IA:** Whisper (transcripción local) + Deepseek (resúmenes)
- **DevOps:** Docker, GitHub Actions

---

## Estructura del Proyecto

```
youtube-AIsummary/
├── docs/                    # Documentación del proyecto
│   ├── contexting-prompts/  # Contexto y roadmap
│   └── professional-prompts/ # Prompts de desarrollo
├── .env.example            # Template variables de entorno
├── .gitignore              # Archivos excluidos de Git
└── README.md               # Este archivo
```

---

## Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles

---

## Estado del Proyecto

**Fase actual:** 0 - Planning & Setup  
**Último update:** Octubre 2025

Ver [docs/contexting-prompts/roadmap.md](docs/contexting-prompts/roadmap.md) para roadmap detallado.
