"""
Tareas asincronas de Celery.

Este modulo contiene todas las tareas de Celery del sistema,
organizadas por dominio funcional.

Tareas disponibles:
- video_processing: Procesamiento del pipeline completo
- maintenance: Limpieza y mantenimiento (futuro)
- discovery: Descubrimiento de nuevos videos (futuro)
- notifications: Envio de notificaciones Telegram (futuro)
"""

from src.tasks.video_processing import process_video_task, retry_failed_video_task

__all__ = [
    "process_video_task",
    "retry_failed_video_task",
]
