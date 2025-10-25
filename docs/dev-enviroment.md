# dev-environment.md

**Proyecto:** `youtube-AIsummary`
**Autor:** Pablo (prodelaya)
**Última actualización:** 25/10/2025
**Propósito:** Documentación **operativa** del entorno de desarrollo híbrido (Windows + WSL2 + VS Code + Claude Code + Docker + PostgreSQL/Redis). Este documento sirve como guía rápida y de referencia para arrancar, mantener y depurar el entorno.

---

## 1) Visión general del setup

Tu configuración combina lo mejor de tres mundos:

- **Windows**: interfaz gráfica, gestores (Docker Desktop), productividad general.
- **WSL2 (Ubuntu)**: entorno Linux real para Python, Poetry, Celery, Redis, PostgreSQL.
- **VS Code (Remote - WSL)**: editor en Windows, ejecución dentro de Ubuntu.
- **Claude Code (VS Code Terminal)**: IA contextual con control humano.
- **Claude Desktop (Acceso por ruta)**: asistente externo para diseño, documentación y revisión de alto nivel.

### Diagrama (Mermaid)

```mermaid
flowchart LR
  subgraph WINDOWS[Windows 10/11]
    VS[VS Code]
    CD[Claude Desktop]
    DD[Docker Desktop]
  end
  subgraph WSL2[WSL2 - Ubuntu]
    PY[Python + Poetry]
    DC[Docker Engine (a través de Docker Desktop)]
    PG[(PostgreSQL)]
    RD[(Redis)]
    CC[Claude Code (CLI/REPL en terminal VS Code)]
    PRJ[/Repo: youtube-AIsummary/]
  end

  VS <-- Remote - WSL --> PRJ
  VS <-- Terminal --> CC
  CD <-- acceso file:// --> PRJ
  DD <-- integración WSL2 --> DC
  DC --> PG
  DC --> RD
  PY --> PRJ
```

---

## 2) Requisitos y versiones mínimas

- **Windows 10/11** con **WSL2** habilitado
- **Ubuntu (WSL2)** actualizado (`sudo apt update && sudo apt upgrade -y`)
- **Docker Desktop** con integración **WSL2** activada
- **Node.js ≥ 18** (para Claude Code CLI)
- **Poetry** instalado en WSL
- **VS Code** + extensión **Remote - WSL**

Comprobaciones rápidas (en **WSL**):
```bash
uname -a                 # Debe decir Linux ... WSL2
node -v && npm -v        # >= 18 y npm presente
poetry --version         # Poetry instalado
docker version           # Docker CLI accesible desde WSL
```

---

## 3) Apertura correcta del proyecto

**Siempre** abre el repo desde **WSL**:

```bash
cd ~/proyectos/youtube-AIsummary
code .
```

Se debe ver en la barra inferior de VS Code: **WSL: Ubuntu**.
El terminal integrado de VS Code debe abrirse en **bash (WSL)**.

**Evitar:** abrir la ruta como `\\wsl.localhost\Ubuntu\...` desde Windows → provoca terminal PowerShell y desincronización del entorno.

---

## 4) Git: configuración recomendada (WSL)

Evita problemas de saltos de línea y autoría:

```bash
git config --global core.autocrlf input
git config --global core.safecrlf true
git config --global user.name "Pablo"
git config --global user.email "tu.email@ejemplo.com"
```

**Opcional (seguridad push):** hook `pre-push` para bloquear pushes automáticos o no firmados:

```bash
cat > .git/hooks/pre-push <<'EOF'
#!/usr/bin/env bash
AUTHOR="$(git config user.email)"
if [[ "$AUTHOR" != "tu.email@ejemplo.com" ]]; then
  echo "❌ Push bloqueado: autor distinto ($AUTHOR)."
  exit 1
fi
if git log -1 --pretty=%B | grep -qiE 'auto-commit|bot|automático'; then
  echo "❌ Push bloqueado: parece commit automático."
  exit 1
fi
exit 0
EOF
chmod +x .git/hooks/pre-push
```

---

## 5) Docker Desktop + WSL2

1. En **Docker Desktop** → *Settings* → **Resources > WSL Integration** → activa tu distro Ubuntu.
2. En WSL prueba:
   ```bash
   docker info | grep -i wsl
   docker ps
   ```
3. Usa `docker-compose.yml` del proyecto para levantar servicios:
   ```bash
   docker-compose up -d
   docker-compose ps
   ```

---

## 6) Dependencias de Python con Poetry (WSL)

```bash
poetry install
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
poetry run celery -A src.core.celery_app worker --loglevel=info
poetry run pytest --cov=src --cov-report=html
poetry run black --check . && poetry run ruff check . && poetry run mypy src/
```

**Consejo:** evita instalar dependencias Python fuera de Poetry para mantener el entorno reproducible.

---

## 7) Claude Code en VS Code (terminal WSL)

1. **Instalación CLI** (en WSL):
   ```bash
   npm install -g @anthropic-ai/claude-code
   claude --version
   ```
2. **Vinculación con el IDE**:
   - Abre terminal integrado en VS Code.
   - Ejecuta `claude`, dentro del REPL usa:
     ```
     /ide
     ```
     y selecciona **VS Code**.
3. **Activar reglas del proyecto**:
   - Ten `CLAUDE.md` en la raíz.
   - Inicia sesión pidiéndole **leer `CLAUDE.md`** y seguir sus reglas.
4. **Permisos** (si quieres reforzar restricciones): `.claude/settings.json`:
   ```json
   {
     "permissions": {
       "deny": ["Bash(git commit:*)", "Bash(git push:*)"]
     }
   }
   ```

**Flujo recomendado:** Claude Desktop para diseño/ documentación; **Claude Code** para cambios con diffs y lotes pequeños.

---

## 8) Roles y prompts (resumen operativo)

| Prompt                       | Rol                       | Cuándo usar                                  |
| ---------------------------- | ------------------------- | -------------------------------------------- |
| `1-project-designer.md`      | Arquitecto                | diseño de features, decisiones de alto nivel |
| `2-incremental-builder.md`   | Desarrollador incremental | implementar código en pasos seguros          |
| `3-code-review--refactor.md` | Revisor/Refactor          | revisar y limpiar código existente           |
| `4-diagnostic-expert.md`     | Diagnóstico/Rendimiento   | bugs, profiling, cuellos de botella          |
| `5-deployment--ops.md`       | DevOps                    | Docker, CI/CD, despliegues                   |
| `6-documentation-mentor.md`  | Documentación             | README, guías, docstrings                    |

**Regla:** Claude debe **anunciar el rol** antes de actuar.

---

## 9) Checklists operativos

### 9.1 Arranque del entorno (día a día)
- [ ] `cd ~/proyectos/youtube-AIsummary && code .` (modo **WSL: Ubuntu**)
- [ ] `docker-compose up -d` (PostgreSQL, Redis)
- [ ] `poetry install` (si hay cambios de deps)
- [ ] `poetry run uvicorn ...` (API), `poetry run celery ...` (worker)
- [ ] `claude` → `/ide` → “Lee CLAUDE.md y respeta las reglas”

### 9.2 Antes de mergear
- [ ] Tests OK: `poetry run pytest -q`
- [ ] Lint OK: `black --check`, `ruff`, `mypy`
- [ ] Revisar diffs generados por Claude por **lotes pequeños**
- [ ] Commit/push **manual** desde WSL

### 9.3 Mantenimiento
- [ ] Actualizar `CLAUDE.md` si cambian reglas/roles
- [ ] Actualizar `architecture.md` tras decisiones relevantes
- [ ] Revisar imágenes Docker y dependencias obsoletas

---

## 10) Troubleshooting (rápido y directo)

**VS Code abre PowerShell (PS …) y no bash**
- Abrir desde WSL: `code .`
- Extensión *Remote - WSL* instalada y habilitada
- Paleta: “WSL: Reopen Folder in WSL”

**Claude no ve diffs ni archivos abiertos**
- Ejecuta `claude` en el **terminal integrado** (no externo)
- `claude` → `/ide` → seleccionar **VS Code**
- Confirmar que estás en la raíz del repo

**Docker no funciona desde WSL**
- Docker Desktop → Settings → Resources → WSL Integration → Ubuntu ON
- `wsl -l -v` (debe ser WSL **2**)
- Reiniciar Docker Desktop y sesión WSL: `wsl --shutdown`

**Saltos de línea raros / CRLF**
- `git config --global core.autocrlf input` y re-clonar si es necesario

**Commits automáticos no deseados**
- Usar `.claude/settings.json` (deny git commit/push) + hook `pre-push`

---

## 11) Añadir este documento al control de versiones

```bash
git add dev-environment.md
git commit -m "docs: añadir documentación del entorno de desarrollo (Windows+WSL+VS Code+Claude)"
git push
```

---

## 12) Apéndice: comandos rápidos (copiar/pegar)

```bash
# Abrir proyecto correctamente
cd ~/proyectos/youtube-AIsummary && code .

# Arrancar servicios
docker-compose up -d && docker-compose ps

# Backend y worker
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
poetry run celery -A src.core.celery_app worker --loglevel=info

# Pruebas y calidad
poetry run pytest --cov=src --cov-report=html
poetry run black --check . && poetry run ruff check . && poetry run mypy src/

# Claude Code
claude   # luego /ide (VS Code) y pedir "Lee CLAUDE.md"
```

---

**Fin del documento.**
Cualquier cambio relevante en herramientas, versiones o flujo de trabajo debe reflejarse aquí y en `CLAUDE.md`.
