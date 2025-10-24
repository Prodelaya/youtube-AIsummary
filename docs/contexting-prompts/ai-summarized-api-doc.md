# 🧠 ApyHub API — Summarize Text Submit Job

## 📍 Endpoint
**POST**  
`https://api.apyhub.com/sharpapi/api/v1/content/summarize`

---

## 🧾 Descripción
La **Summarize Text API** genera un resumen de texto a partir de un contenido largo utilizando IA.  
Permite personalizar el tono, la longitud máxima y el idioma del resumen.

Ideal para automatizar la creación de resúmenes de artículos, transcripciones o documentos extensos.

---

## 🚀 Ejemplo de solicitud (cURL)

    curl --request POST \
      --url https://api.apyhub.com/sharpapi/api/v1/content/summarize \
      --header 'Content-Type: application/json' \
      --header 'apy-token: APY02EiFj9TIO1dkhkVD1OpS0UnSzeHzGnHIcbuP0LyRtTcqdBUUjlWLMFZBAXg6x7nm7REg8V2d' \
      --data '{
        "content": "Red Bulls Max Verstappen says this weekends Las Vegas Grand Prix is 99% show and 1% sporting event. \n\n The triple world champion said he is not looking forward to the razzmatazz around the race, the first time Formula 1 cars have raced down the citys famous Strip. \n\n Other leading drivers were more equivocal about the hype.\n\n Aston Martins Fernando Alonso said: With the investment that has been made and the place we are racing, it deserves a little bit [of] different treatment and extra show. \n\n The weekend was kick-started on Wednesday evening with a lavish opening ceremony.\n\n It featured performances from several music stars, including Kylie Minogue and Journey, and culminated in the drivers being introduced to a sparsely populated crowd in light rain by being lifted into view on hydraulic platforms under a sound-and-light show. \n\n Lewis Hamilton said: Its amazing to be here. It is exciting - such an incredible place, so many lights, a great energy, a great buzz. \n\n This is one of the most iconic cities there is. It is a big show, for sure. It is never going to be like Silverstone [in terms of history and purity]. But maybe over time the people in the community here will grow to love the sport. \n\n Hamilton added: It is a business, ultimately. Youll still see good racing here. \n\n Maybe the track will be good, maybe it will be bad. It was so-so on the [simulator]. Dont knock it til you try it. I hear there are a lot of people complaining about the direction [F1 president] Stefano [Domenicali] and [owners] Liberty have been going [but] I think they have been doing an amazing job.",
        "voice_tone": "Funny, Adventurous",
        "max_length": "250",
        "language": "English"
      }'

---

## ⚙️ Parámetros de la solicitud

| Atributo     | Tipo   | Obligatorio | Descripción                                                                                 |
|--------------|--------|-------------|---------------------------------------------------------------------------------------------|
| `content`    | String | ✅ Sí       | Texto a resumir.                                                                            |
| `context`    | String | ❌ No       | Instrucciones adicionales para el procesamiento del contenido.                              |
| `voice_tone` | String | ❌ No       | Tono del resumen (p. ej., `funny`, `serious`, `joyous`, o nombre de un escritor).           |
| `max_length` | Number | ❌ No       | Longitud máxima del resumen (en palabras). Ejemplo: `100`.                                  |
| `language`   | String | ❌ No       | Idioma del resumen (por defecto: `English`).                                                |

---

## 🧩 Encabezados HTTP

| Encabezado                     | Descripción                                                     |
|--------------------------------|-----------------------------------------------------------------|
| `Content-Type: application/json` | Indica el tipo de contenido del cuerpo de la solicitud.      |
| `apy-token: <API_KEY>`         | Token de autenticación generado desde tu cuenta de ApyHub.     |

---

## 📦 Ejemplo de respuesta

    {
      "status_url": "https://api.apyhub.com/sharpapi/api/v1/content/summarize/job/status/5de4887a-0dfd-49b6-8edb-9280e468c210",
      "job_id": "5de4887a-0dfd-49b6-8edb-9280e468c210"
    }

> La API es **asíncrona**, por lo que devuelve un `job_id` y una `status_url` donde puedes consultar el estado del resumen.

---

## 🔁 Códigos de respuesta HTTP

| Código | Descripción                                                                                  |
|-------:|----------------------------------------------------------------------------------------------|
| **202** | El trabajo se ha enviado correctamente.                                                     |
| **400** | Entrada inválida (por ejemplo, JSON mal formado o contenido corrupto).                      |
| **401** | Falta autenticación o el token no es válido.                                                |
| **500** | Error interno del servidor.                                                                 |

---

## 🔐 Autenticación

Todos los endpoints requieren autenticación mediante **API Token** o **Basic Auth**.

- Puedes generar tu token desde: **Dashboard → Workspace → API Keys**  
- Usa el header `apy-token` para enviar el token.  
- Los secretos **no se almacenan en texto plano**: guarda tu token de forma segura.

---

## ⚠️ Códigos de error

| Código | Descripción                                                                                                             |
|------:|-------------------------------------------------------------------------------------------------------------------------|
| **101** | Faltan parámetros obligatorios (por ejemplo, `content`).                                                              |
| **102** | JSON inválido en el cuerpo de la solicitud.                                                                           |
| **103** | Entrada inválida (datos incorrectos o fuera de rango).                                                                |
| **104** | Archivo no válido o ausente.                                                                                          |
| **105** | URL inválida o inaccesible.                                                                                           |
| **109** | Formato de entrada incorrecto (p. ej., número en lugar de texto).                                                     |
| **110** | Error interno del servidor durante el procesamiento.                                                                   |

### Ejemplo de error

    {
      "error": {
        "code": 105,
        "message": "Invalid URL"
      }
    }

---

## 🧠 Notas importantes

- Guarda tus credenciales en un lugar seguro.  
- Cada petición consume 1 de tus **10 llamadas AI diarias** en el plan gratuito.  
- El endpoint devuelve un trabajo asíncrono; recuerda consultar el `status_url`.  
- Si procesas grandes volúmenes de texto, puedes dividir el contenido en bloques.  

---

📚 **Referencia oficial:** ApyHub — Summarize Text API
