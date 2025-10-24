# 🧠 Proyecto: youtube-AIsummary — Plataforma de Resúmenes Inteligentes sobre Innovaciones en IA

## 🎯 Objetivo General

**IA Monitor** es un proyecto diseñado con una doble finalidad:

1. **Mantenerte informado sobre la actualidad de la Inteligencia Artificial aplicada al desarrollo de software**, mediante un sistema automático que recopila, analiza y resume las novedades más relevantes del sector (nuevas tecnologías, frameworks, herramientas, librerías y metodologías útiles para desarrolladores).

2. **Servir como proyecto de portfolio profesional**, demostrando dominio de las tecnologías y buenas prácticas modernas en el desarrollo **backend con Python**, orientadas a la arquitectura de microservicios, APIs escalables, observabilidad, integración de IA y despliegue en contenedores.

---

## 💡 Idea Central del Proyecto

El sistema se comporta como un **agregador inteligente de información sobre IA y desarrollo de software**.  
Cada día o semana, el sistema:

1. **Explora fuentes relevantes** (YouTube, blogs técnicos, canales especializados, podcasts, newsletters de IA, etc.).  
2. **Transcribe** los contenidos mediante **Whisper**, un modelo open source de reconocimiento de voz.  
3. **Resume** las transcripciones usando la **API de ApyHub**, generando un texto conciso y coherente que captura los puntos más importantes del contenido.  
4. **Clasifica y almacena** los resúmenes según temática (IA aplicada a frontend, backend, productividad, testing, cloud, etc.).  
5. **Publica y notifica** los resultados a través de distintos canales: API REST, dashboard web o Telegram bot.

El usuario final (por ejemplo, un desarrollador o investigador) recibe **una selección de resúmenes de alta calidad** sobre la actualidad tecnológica en IA sin tener que revisar manualmente horas de vídeos o artículos.

---

## 🎯 Objetivos Principales

### 1. Mantenerse informado sobre la evolución de la IA en el desarrollo de software

El sistema detecta y resume automáticamente los contenidos más recientes sobre:

- Nuevas **librerías y frameworks de IA** útiles para el desarrollo (LangChain, OpenDevin, Semantic Kernel, etc.).
- **Casos de uso** de la IA en diferentes etapas del desarrollo (desde testing hasta documentación).
- **Herramientas emergentes** que aumentan la productividad de programadores.
- **Tendencias en automatización**, MLOps y agentes de software.

> Resultado: un flujo constante de información sintetizada que mantiene actualizado al desarrollador sin esfuerzo manual.

---

### 2. Crear un proyecto de portfolio sólido, atractivo para reclutadores

El sistema está pensado para **mostrar dominio técnico real** en desarrollo backend Python moderno, aplicando tecnologías y patrones que se usan en entornos profesionales.

---

## 🧩 Arquitectura General

```mermaid
graph LR
    A[YouTube / RSS / API Sources] --> B[Downloader]
    B --> C[Whisper Transcriber]
    C --> D[ApyHub Summarizer]
    D --> E[Classifier & Database]
    E --> F[REST API (FastAPI)]
    E --> G[Telegram / Dashboard Delivery]
    F --> H[Monitoring (Prometheus + Grafana)]
```

### Flujo resumido
1. **Extracción** → obtiene contenidos recientes.
2. **Transcripción** → Whisper convierte audio a texto.
3. **Resumen** → ApyHub resume el texto.
4. **Clasificación y almacenamiento** → se guarda en PostgreSQL con etiquetas temáticas.
5. **Distribución** → API REST y/o canal de Telegram.
6. **Monitorización** → métricas en Prometheus/Grafana para medir rendimiento y estado.

---

## 🧠 Tecnologías Clave

### 🔹 Lenguaje y entorno
- **Python 3.11** — moderno, tipado, soporte async.
- **Poetry** — gestión de dependencias y entorno virtual.
- **Docker + Docker Compose** — contenedores reproducibles.

### 🔹 Backend
- **FastAPI** — framework asíncrono para la API REST.
- **SQLAlchemy 2.0 + Alembic** — ORM y migraciones de base de datos.
- **PostgreSQL** — base de datos relacional.
- **Redis / Celery** — tareas en segundo plano (descargas, transcripciones, polling).
- **httpx + Tenacity** — cliente asíncrono robusto con reintentos y timeouts.

### 🔹 IA e Integraciones
- **Whisper (OpenAI)** — transcripción local gratuita.
- **ApyHub Summarization API** — resumen de texto con IA mediante API externa.

### 🔹 DevOps y Observabilidad
- **Prometheus + Grafana + Loki** — métricas, logs y alertas.
- **OpenTelemetry** — trazas distribuidas.
- **Ruff + Black + mypy + pytest** — estilo, tipado y testing.
- **GitHub Actions** — integración y despliegue continuo.

---

## 🧰 Diseño Técnico (resumen conceptual)

| Etapa | Descripción | Tecnología |
|-------|--------------|-------------|
| **1. Ingesta** | Descarga de vídeos y audios (YouTube API, RSS) | `yt-dlp`, `asyncio`, `Celery` |
| **2. Transcripción** | Conversión de audio a texto | `Whisper` |
| **3. Resumen** | Resumen automático del texto | `ApyHub API` |
| **4. Clasificación** | Identificación temática y etiquetado | `spaCy`, `scikit-learn` (opcional) |
| **5. Persistencia** | Almacenamiento de resultados | `PostgreSQL + SQLAlchemy` |
| **6. Exposición** | API REST / Telegram / Dashboard | `FastAPI` |
| **7. Monitorización** | Métricas y logs centralizados | `Prometheus`, `Grafana`, `Loki` |

---

## 🌍 Valor educativo y profesional

### 🧠 Formación técnica
Permite aprender y practicar con:
- Pipelines asíncronos reales (descarga → transcripción → resumen → entrega).
- Integración de APIs externas (ApyHub, Telegram, YouTube).
- Procesamiento de lenguaje natural (NLP).
- Arquitectura limpia basada en etapas (separación clara por responsabilidad).
- DevOps básico con observabilidad y CI/CD.

### 💼 Valor en el portfolio
El proyecto demuestra:
- **Uso avanzado de FastAPI y asincronía.**
- **Diseño modular y escalable**, con integración de IA.
- **Conocimientos de orquestación y automatización de procesos.**
- **Prácticas de ingeniería profesional:** pruebas, métricas, seguridad y despliegue.

> Es un proyecto que **cuenta una historia técnica**: cómo un backend moderno puede automatizar tareas cognitivas usando IA real.

---

## 📈 Posibilidades de expansión futura

- Integración con **Google Trends o Reddit API** para detectar temas emergentes.  
- Sistema de recomendación basado en intereses (machine learning).  
- Dashboard web con filtros por temática y fuente.  
- Generación de boletines automáticos con los mejores resúmenes.  
- Exportación a Notion o Medium con formato Markdown.

---

## 🧭 Conclusión

**IA Monitor** combina **aprendizaje práctico de backend Python** con **utilidad real** para mantenerse al día sobre la evolución de la IA en el desarrollo de software.  

Su diseño modular y uso de tecnologías profesionales lo convierten en un **proyecto ideal de portfolio**, capaz de demostrar competencias sólidas en:

- Desarrollo backend moderno (FastAPI, asyncio, PostgreSQL, Docker)
- Integración de APIs de IA reales (Whisper, ApyHub)
- Arquitectura limpia, trazable y observable
- Buenas prácticas de ingeniería de software

> En resumen: **una plataforma de información útil y un escaparate técnico sólido** para destacar como desarrollador backend Python en el mercado laboral actual.
