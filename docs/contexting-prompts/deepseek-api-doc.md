# 🧠 DeepSeek API — Documentación para Resúmenes de Texto

## 📍 Endpoint Principal
**POST**  
`https://api.deepseek.com/chat/completions`

---

## 🧾 Descripción
La **DeepSeek Chat API** es compatible con el formato OpenAI y permite generar resúmenes de texto mediante el modelo `deepseek-chat`. 

Características destacadas:
- API síncrona (respuesta inmediata, sin polling)
- Compatible con SDK de OpenAI
- Context caching automático (reduce costos hasta 80%)
- JSON output nativo
- Sin límites artificiales de uso

---

## 🚀 Ejemplo básico (Python con OpenAI SDK)

```python
from openai import OpenAI

# Configurar cliente (compatible con DeepSeek)
client = OpenAI(
    api_key="<your_deepseek_api_key>",
    base_url="https://api.deepseek.com"
)

# Generar resumen
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {
            "role": "system",
            "content": "Eres un asistente que genera resúmenes concisos en español."
        },
        {
            "role": "user",
            "content": "Resume el siguiente texto: [tu texto aquí]"
        }
    ],
    max_tokens=1000,
    temperature=0.7,
    stream=False
)

print(response.choices[0].message.content)
```

---

## ⚙️ Parámetros principales

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `model` | String | ✅ Sí | Modelo a usar: `deepseek-chat` o `deepseek-reasoner` |
| `messages` | Array | ✅ Sí | Lista de mensajes del chat (system, user, assistant) |
| `max_tokens` | Integer | ❌ No | Máximo de tokens a generar (default: 4K, max: 8K) |
| `temperature` | Number | ❌ No | Temperatura de muestreo (0-2, default: 1) |
| `top_p` | Number | ❌ No | Nucleus sampling (0-1, default: 1) |
| `stream` | Boolean | ❌ No | Streaming de respuesta (SSE) |
| `response_format` | Object | ❌ No | Forzar JSON output: `{"type": "json_object"}` |

---

## 📦 Ejemplo de respuesta

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1730000000,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Este es el resumen generado..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 120,
    "total_tokens": 570,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 450
  }
}
```

---

## 💰 Pricing (Modelo deepseek-chat)

| Concepto | Precio por 1M tokens |
|----------|---------------------|
| **Input (cache miss)** | $0.28 |
| **Input (cache hit)** | $0.028 (90% descuento) |
| **Output** | $0.42 |

**Ejemplo de costo mensual (300 videos):**
- Transcripción promedio: 4,700 tokens
- Resumen promedio: 400 tokens
- **Sin cache:** ~$0.45/mes
- **Con cache (80% hit rate):** ~$0.16/mes

---

## 🔁 Context Caching

DeepSeek implementa **context caching automático en disco**:
- Cache hit si el prefijo del prompt coincide con una solicitud previa
- El contenido cacheado NO consume cuota de input normal
- Útil para prompts con prefijos repetidos (system messages, few-shot examples)
- TTL: Días/semanas (se limpia automáticamente)

**Campos en response:**
- `prompt_cache_hit_tokens`: Tokens leídos desde cache ($0.028/1M)
- `prompt_cache_miss_tokens`: Tokens procesados normalmente ($0.28/1M)

**Ejemplo de optimización:**

```python
# Primera llamada: construye cache
messages = [
    {"role": "system", "content": "Eres un experto..."},  # Se cachea
    {"role": "user", "content": "Resume: [texto 1]"}
]

# Segunda llamada: reutiliza cache
messages = [
    {"role": "system", "content": "Eres un experto..."},  # Cache hit!
    {"role": "user", "content": "Resume: [texto 2]"}
]
```

---

## 📋 JSON Output

Para obtener respuestas estructuradas:

```python
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {
            "role": "system",
            "content": """Genera resúmenes en formato JSON con esta estructura:
            {
              "summary": "texto del resumen",
              "keywords": ["palabra1", "palabra2"],
              "language": "Spanish"
            }"""
        },
        {"role": "user", "content": "Resume: [tu texto]"}
    ],
    response_format={"type": "json_object"}
)

import json
result = json.loads(response.choices[0].message.content)
```

---

## 🔐 Autenticación

**API Key:**
- Obtener desde: https://platform.deepseek.com/
- Configurar como variable de entorno: `DEEPSEEK_API_KEY`
- **NO usar `x-api-key` header**, usar configuración del cliente OpenAI

```python
# Correcto ✅
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# Incorrecto ❌ (no uses headers custom)
# headers = {"x-api-key": "..."}
```

---

## ⚠️ Códigos de error HTTP

| Código | Descripción | Solución |
|--------|-------------|----------|
| **400** | Formato de request inválido | Verificar JSON y parámetros |
| **401** | API key inválida o faltante | Revisar autenticación |
| **429** | Rate limit alcanzado | Reducir frecuencia de requests |
| **500** | Error interno del servidor | Reintentar tras breve espera |
| **503** | Servidor sobrecargado | Reintentar con backoff exponencial |

---

## 🎯 Mejores prácticas para resúmenes

### 1. System Prompt efectivo

```python
system_prompt = """
Eres un asistente especializado en crear resúmenes concisos de transcripciones de vídeos técnicos.

REGLAS:
1. Resumen en español (idioma original)
2. Máximo 250 palabras
3. Formato: párrafo único, tono profesional
4. Incluir: tema principal, 3-5 puntos clave
5. Omitir: saludos, despedidas, muletillas
"""
```

### 2. Estructura del user prompt

```python
user_prompt = f"""
Transcripción del vídeo "{video_title}" (duración: {duration}):

---
{transcription_text}
---

Genera un resumen siguiendo las reglas del system prompt.
"""
```

### 3. Parámetros recomendados

```python
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[...],
    max_tokens=500,        # Suficiente para resumen de 250 palabras
    temperature=0.3,       # Baja para respuestas consistentes
    top_p=0.9,            # Nucleus sampling
    response_format={"type": "json_object"}  # Si necesitas estructura
)
```

---

## 🧩 Integración con proyecto

**Dependencias necesarias:**
```bash
poetry add openai  # SDK compatible con DeepSeek
```

**Variables de entorno (.env):**
```bash
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

**Configuración (src/core/config.py):**
```python
class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str = Field(min_length=10)
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
```

---

## 📊 Limitaciones y restricciones

| Aspecto | Límite |
|---------|--------|
| **Context length** | 128K tokens (~100K palabras) |
| **Max output** | 8K tokens (default: 4K) |
| **Rate limit** | Sin límite documentado (fair use) |
| **Request timeout** | Configurar en cliente (recomendado: 60s) |

---

## 🔗 Referencias útiles

- **Documentación oficial:** https://api-docs.deepseek.com/
- **Platform (API keys):** https://platform.deepseek.com/
- **Pricing details:** https://platform.deepseek.com/pricing
- **API Status:** https://status.deepseek.com/

---

**Nota:** Este documento está optimizado para el proyecto youtube-AIsummary. Para casos de uso más complejos (function calling, reasoning mode), consultar documentación oficial.
