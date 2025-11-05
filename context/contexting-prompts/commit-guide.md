# Guía de Convenciones de Commits (Conventional Commits) — Proyecto Python

> **Objetivo**: estandarizar los mensajes de commit para que una IA (p. ej., Claude) pueda **generarlos**, **validarlos** y **producir changelogs** automáticamente.
> **Regla de oro**: *un commit = un cambio lógico atómico*.

---

## 1) Formato canónico

```
<type>(<scope>)!: <subject>
<blank line>
<body>
<blank line>
<footer>
```

- **type** *(obligatorio)*: categoría del cambio (ver §2).
- **scope** *(opcional)*: módulo/área afectada (ver §3).
- **!** *(opcional)*: hay **breaking change**.
- **subject** *(obligatorio)*: en **imperativo**, **minúscula**, **sin punto final**, ≤ 50 chars.
- **body** *(opcional recomendado)*: explica **qué problema** se resuelve y **por qué** así. Envuelve a ~72 chars; puede llevar bullets.
- **footer** *(opcional)*: metadatos. Ej.: `BREAKING CHANGE: ...`, `Closes #123`, `Refs #45`, `Co-authored-by: ...`.

### Ejemplos válidos

```
feat(api): añade endpoint GET /health
```

```
fix(auth): evita 500 cuando falta el header Authorization

Se valida el token antes de acceder a user_id. Añadido test de integración.
Closes #231
```

```
feat(db)!: renombra columna username -> handle en users

BREAKING CHANGE: los clientes deben usar 'handle' en lugar de 'username'.
Incluye migración 20251028_rename_username_to_handle.
```

---

## 2) Tipos permitidos

| Tipo       | Uso principal                                                           |
| ---------- | ----------------------------------------------------------------------- |
| `feat`     | Nueva **funcionalidad** visible para el usuario o API                   |
| `fix`      | **Corrección de bug**                                                   |
| `docs`     | Documentación (README, docstrings, mkdocs, etc.)                        |
| `style`    | Cambios de estilo **sin lógica** (formato, imports, tipado superficial) |
| `refactor` | Reestructuración interna **sin cambiar comportamiento público**         |
| `perf`     | Mejora de **rendimiento**                                               |
| `test`     | Añadir/ajustar **tests**                                                |
| `build`    | Sistema de build/deps (poetry/pip, Dockerfile, Makefile, pyproject)     |
| `ci`       | Pipelines CI/CD (GitHub Actions, GitLab CI)                             |
| `chore`    | Tareas auxiliares sin afectar a `src` funcional (scripts, housekeeping) |
| `revert`   | Revertir un commit anterior                                             |

> Extensiones opcionales si aportan claridad: `security`, `deps`, `i18n`, `ux`.
> Úsalas **solo** si el equipo las adopta explícitamente.

---

## 3) Scopes recomendados (Proyecto Python)

Usa un **scope** corto, estable y consistente.

- `api`, `auth`, `users`, `payments`
- `models`, `schemas`, `services`, `repositories`
- `db`, `migrations`
- `cli`, `config`
- `jobs`, `tasks`, `scheduler`
- `infra`, `docker`, `k8s`
- `tests`, `docs`
- `deps`, `ci`

**Ejemplos**:
- `feat(api): añade filtro por email en /users`
- `refactor(services): extrae PaymentService`
- `build(deps): bump fastapi 0.115 -> 0.116`
- `perf(db): añade índice compuesto (user_id, created_at)`

---

## 4) Reglas de estilo

- **Subject**: verbo en **imperativo** y **minúscula**: “añade”, “corrige”, “refactoriza”, “mejora”.
  ✅ `fix(parser): maneja emojis`
  ❌ `Arreglado parser`, `Arreglando parser`, `Fix parser.`
- **Sin punto** al final del subject.
- **No mezclar cambios no relacionados** en el mismo commit.
- **El body explica el porqué** y el impacto, no el “cómo” (eso ya está en el diff).
- **Longitud**: subject ≤ 50 chars; cuerpo envuelto a ~72 chars.

---

## 5) Breaking changes

Marca breaking de **una** de estas formas:

1. `!` tras el scope en el encabezado:
   `feat(api)!: cambia contrato de /users`
2. En el **footer** con etiqueta **obligatoria**:
   ```
   BREAKING CHANGE: /users ahora requiere token JWT y devuelve 'handle'
   ```

> Siempre explica **qué rompe**, **impacto** y **pasos de migración**.

---

## 6) Footer: metadatos útiles

- **Issues/PRs**: `Closes #123`, `Refs #456`
- **Co-authors**: `Co-authored-by: Nombre <email>`
- **Security**: `CVE-XXXX-YYYY`, `Refs advisory GHSA-...`

---

## 7) Tabla de mapeo “cambio → type/scope”

| Cambio detectado                           | Sugerencia de commit                             |
| ------------------------------------------ | ------------------------------------------------ |
| Añades endpoint nuevo                      | `feat(api): ...`                                 |
| Cambias respuesta/contrato de un endpoint  | `feat(api)!: ...` + `BREAKING CHANGE: ...`       |
| Corriges excepción, 500, validación        | `fix(<scope>): ...`                              |
| Añades/mutas migración de DB               | `feat(db): ...` o `fix(db): ...` (según impacto) |
| Renombras columnas/tablas                  | `feat(db)!: ...` + `BREAKING CHANGE: ...`        |
| Refactor interno sin cambios funcionales   | `refactor(<scope>): ...`                         |
| Índices, caché, batch, vectorización       | `perf(<scope>): ...`                             |
| Nuevos tests o corrigen flaky tests        | `test(<scope>): ...`                             |
| Actualizas deps/lockfiles/poetry/pyproject | `build(deps): ...`                               |
| Cambios en GH Actions/CI                   | `ci: ...`                                        |
| README, docsstring, mkdocs                 | `docs(<scope>): ...`                             |
| Formateo, imports, tipado superficial      | `style(<scope>): ...`                            |

---

## 8) Ejemplos completos (Python)

**Feature con body y referencia**
```
feat(users): añade búsqueda por email

Se incorpora query param ?email=... y validación en schema.
Incluye test de integración p95 < 30ms.
Closes #102
```

**Fix + test**
```
fix(auth): corrige verificación exp de JWT

El parser rechazaba tokens válidos por drift de 30s.
Se añade tolerancia y test unitario.
```

**DB breaking + migración**
```
feat(db)!: renombra username -> handle en tabla users

BREAKING CHANGE: el modelo User expone 'handle' en lugar de 'username'.
Incluye migración 20251028_rename_username_to_handle y adaptación de seeds.
```

**Rendimiento**
```
perf(services): memoiza get_user_settings con TTL 5m

Reduce hits a DB en p95 un 82% en /me.
```

**Dependencias**
```
build(deps): actualiza fastapi 0.115 -> 0.116
```

---

## 9) “Do / Don’t” (errores típicos)

- ❌ `update`, `misc`, `cosas`, `arreglo` genéricos
  ✅ Sé específico: `fix(auth): maneja tokens expirados`
- ❌ Subject con punto final o mayúscula inicial sin motivo
  ✅ minúscula y sin punto: `refactor(db): separa repos`
- ❌ Mezclar refactor + feature + formatting en el mismo commit
  ✅ Divide en commits atómicos.
- ❌ Body que describe código línea a línea
  ✅ Explica **problema**, **decisión** e **impacto**.

---

## 10) Plantilla para el body (opcional pero recomendada)

Puedes usar este bloque en tus commits “grandes”:

```
Contexto:
- [qué problema/limitación había]
- [quién/qué lo sufre]

Decisión:
- [enfoque elegido y por qué]
- [alternativas consideradas (si aplica)]

Impacto:
- [cambios visibles / métricas / riesgos / migración]
```

---

## 11) Cómo debe usarlo la IA (Claude) para generar commits

> **Entrada recomendada para la IA**: *diff conciso*, archivos tocados, tests añadidos, intención del cambio (si aplica) y si hay breaking.

### Prompt de sistema (resumen)

> Eres un generador de mensajes de commit siguiendo “Conventional Commits”.
> Debes producir **solo** un commit con el formato `<type>(<scope>)!: <subject>` + body + footer.
> Usa español (es-ES), imperativo, minúscula y sin punto final en el subject.
> Valida que el **type** esté en la lista de §2 y el **scope** en §3 (si procede).
> Marca breaking con `!` y un `BREAKING CHANGE:` en footer cuando aplique.
> Si el diff mezcla cambios no relacionados, **sugiere** dividir en varios commits (pero entrega la mejor opción atómica posible).

### Esquema de entrada (ejemplo)

```yaml
intent: "añadir búsqueda por email en /users y test"
breaking: false
files_changed:
  - path: src/api/users.py
    change: "add endpoint param email"
  - path: src/schemas/user.py
    change: "add EmailStr field"
  - path: tests/test_users_search.py
    change: "new"
diff_summary: |
  + GET /users?email=...
  + validate email format
  + integration test p95 28ms
issues:
  closes: [102]
```

### Salida esperada (ejemplo)

```
feat(api): añade búsqueda por email

Se valida formato y se añade test de integración p95 < 30ms.
Closes #102
```

### Checklist de validación (que debe aplicar la IA)

- [ ] El **type** es uno de §2.
- [ ] **Subject** en imperativo, minúscula, sin punto, ≤ 50 chars.
- [ ] **Scope** coherente con §3.
- [ ] **Body** explica porqué/impacto (no el cómo detallado).
- [ ] Si hay ruptura, añade `!` y `BREAKING CHANGE:`.
- [ ] Incluye `Closes #N`/`Refs #N` si se proporcionan issues.

---

## 12) Snippets reutilizables

**Template vacío**
```
<type>(<scope>)<optional-!>: <subject>

[Contexto/Decisión/Impacto en 1–5 líneas]

[BREAKING CHANGE: <impacto y pasos de migración>]
[Closes|Refs #<número>]
```

**Refs múltiples**
```
fix(api): normaliza errores 4xx en login

Unifica estructura de error para clientes.
Refs #120 #121
```

---

## 13) Preguntas frecuentes

- **¿Puedo omitir el scope?** Sí, pero **mejor inclúyelo** cuando aporte contexto.
- **¿Dónde pongo una migración?** En `feat(db): ...` si añade capacidad; `fix(db): ...` si corrige; usa `!` si rompe compatibilidad.
- **¿Docs y code juntos?** Si el cambio de docs describe la feature del commit, puede ir junto. Si es refactor + docs no críticos, sepáralo.

---

**Resumen**: usa `type(scope): subject` con imperativo/minúscula, explica el porqué en el body, y marca breaking con `!` + `BREAKING CHANGE:`. Esta guía permite a una IA generar commits útiles, consistentes y compatibles con versionado semántico y changelogs automáticos.
