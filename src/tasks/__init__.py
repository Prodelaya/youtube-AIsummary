"""
Tareas asincronas de Celery.

Este modulo contiene todas las tareas de Celery del sistema,
organizadas por dominio funcional.

Tareas disponibles:
- video_processing: Procesamiento del pipeline completo
- distribute_summaries: Distribución de resúmenes vía Telegram
- maintenance: Limpieza y mantenimiento (futuro)
- discovery: Descubrimiento de nuevos videos (futuro)
"""

from src.tasks.distribute_summaries import distribute_summary_task
from src.tasks.video_processing import process_video_task, retry_failed_video_task

__all__ = [
    "process_video_task",
    "retry_failed_video_task",
    "distribute_summary_task",
]
