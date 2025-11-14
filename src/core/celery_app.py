"""
Configuracion de Celery para tareas asincronas.

Este modulo configura Celery como broker de tareas asincronas usando Redis
como backend de mensajeria y almacenamiento de resultados.

Celery maneja:
- Procesamiento de videos (pipeline completo)
- Reintentos automaticos con exponential backoff
- Distribucion de carga entre multiples workers
- Monitoreo con Flower
- Tareas programadas con Celery Beat (futuro)

Uso:
    # Iniciar worker
    celery -A src.core.celery_app worker --loglevel=info

    # Iniciar Flower (monitoring)
    celery -A src.core.celery_app flower

    # Encolar tarea desde codigo
    from src.tasks.video_processing import process_video_task
    task = process_video_task.delay(str(video_id))
"""

from celery import Celery

from src.core.config import settings

# ==================== CONFIGURACION CELERY ====================

celery_app = Celery(
    "youtube_aisummary",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.tasks.video_processing",
        "src.tasks.distribute_summaries",
        "src.tasks.scraping",
    ],  # Auto-discover tasks
)

# Configuracion del broker y backend
celery_app.conf.update(
    # Serializacion
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task tracking
    task_track_started=True,  # Registrar cuando inicia una tarea
    task_send_sent_event=True,  # Enviar eventos de tareas
    # Timeouts
    task_time_limit=3600,  # 1 hora max por tarea (hard limit)
    task_soft_time_limit=3300,  # 55 min warning (soft limit)
    # Worker optimization
    worker_prefetch_multiplier=1,  # 1 tarea a la vez (Whisper consume mucha RAM)
    worker_max_tasks_per_child=10,  # Reiniciar worker cada 10 tareas (prevenir memory leaks)
    # Result backend
    result_expires=86400,  # Resultados expiran en 24 horas
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    # Retry policy default
    task_acks_late=True,  # Acknowledge solo despues de completar (prevenir perdida de tareas)
    task_reject_on_worker_lost=True,  # Reencolar si worker muere
    # Monitoring
    worker_send_task_events=True,  # Habilitar eventos para Flower
)

# ==================== TASK ROUTES ====================
# Configurar rutas de tareas a queues especificas

celery_app.conf.task_routes = {
    "src.tasks.video_processing.process_video_task": {
        "queue": "video_processing",  # Queue dedicada para videos
        "routing_key": "video.process",
    },
    "src.tasks.video_processing.retry_failed_video_task": {
        "queue": "video_processing",
        "routing_key": "video.retry",
    },
    "src.tasks.distribute_summaries.distribute_summary_task": {
        "queue": "distribution",  # Queue dedicada para distribución
        "routing_key": "summary.distribute",
    },
    "src.tasks.scraping.sync_youtube_sources_task": {
        "queue": "scraping",  # Queue dedicada para scraping
        "routing_key": "scraping.sync",
    },
}

# ==================== TASK PRIORITIES ====================
# Definir prioridades (0 = lowest, 9 = highest)

celery_app.conf.task_default_priority = 5
celery_app.conf.broker_transport_options = {
    "priority_steps": list(range(10)),  # 0-9 priority levels
}

# ==================== BEAT SCHEDULE ====================
# Tareas programadas (cron-like)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "sync-youtube-channels": {
        "task": "sync_youtube_sources",
        "schedule": crontab(hour="*/6"),  # Cada 6 horas (00:00, 06:00, 12:00, 18:00)
        "options": {
            "queue": "scraping",
            "priority": 7,
        },
    },
}

# ==================== LOGGING ====================

celery_app.conf.worker_hijack_root_logger = False  # No sobrescribir logging config
celery_app.conf.worker_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
)
celery_app.conf.worker_task_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s] "
    "[%(task_name)s(%(task_id)s)] %(message)s"
)
