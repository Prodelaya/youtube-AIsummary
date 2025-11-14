# ADR-013: Frecuencia de Scraping de Canales de YouTube

**Fecha:** 2025-11-14
**Estado:** Aceptado
**Autor:** Claude + Pablo

---

## Contexto

El sistema necesita detectar automáticamente nuevos videos de los canales suscritos sin intervención manual. La pregunta es: **¿Con qué frecuencia debemos escanear los canales?**

## Decisión

**Scraping cada 6 horas** (4 ejecuciones diarias a las 00:00, 06:00, 12:00, 18:00 UTC).

## Justificación

### Factores considerados

1. **Frecuencia de publicación de canales IA/Programming:**
   - La mayoría publican 1-2 videos por semana
   - No hay necesidad de escanear cada hora

2. **Latencia aceptable:**
   - 6 horas de latencia máxima es razonable para contenido educativo
   - No es crítico entregar en tiempo real

3. **Carga del sistema:**
   - 4 scrapings/día × 10 canales = 40 peticiones/día a YouTube
   - Evita rate limits de YouTube
   - Bajo consumo de recursos del servidor

4. **Experiencia del usuario:**
   - Usuarios reciben actualizaciones frecuentes (4x/día)
   - Balance entre frescura y spam

### Alternativas descartadas

| Frecuencia | Ventajas | Desventajas | ¿Por qué NO? |
|------------|----------|-------------|--------------|
| **1 hora** | Latencia mínima | Sobrecarga innecesaria | Canales no publican cada hora |
| **12 horas** | Menos carga | Latencia alta | Muy lento para usuarios activos |
| **24 horas** | Carga mínima | Latencia de 1 día | Inaceptable para sistema "automático" |

## Consecuencias

### Positivas ✅
- Sistema se siente "automático" sin ser agresivo
- Bajo riesgo de rate limits de YouTube
- Recursos del servidor bien utilizados
- 4 ventanas de actualización diarias

### Negativas ⚠️
- Latencia máxima de 6 horas (aceptable)
- No apto para contenido en vivo (no es el caso de uso)

## Implementación

```python
# src/core/celery_app.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "sync-youtube-channels": {
        "task": "sync_youtube_sources",
        "schedule": crontab(hour="*/6"),  # Cada 6 horas
        "options": {"queue": "scraping", "priority": 7},
    },
}
```

## Notas

- Frecuencia configurable en futuro via variable de entorno
- Monitorear métricas de YouTube rate limit en producción
- Considerar ajuste si canales específicos publican más frecuentemente
