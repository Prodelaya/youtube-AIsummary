"""
Sistema de métricas centralizado con Prometheus.

Este módulo proporciona un singleton para todas las métricas del sistema,
asegurando consistencia en nombres, labels y tipos de métricas.

Tipos de métricas:
- Counter: Operaciones incrementales (videos_processed_total)
- Gauge: Valores que suben/bajan (active_celery_workers)
- Histogram: Distribución de valores (video_processing_duration_seconds)
- Summary: Percentiles sin buckets (transcription_duration_quantile)

Convenciones de nombres:
- lowercase con snake_case
- sufijo _total para counters
- sufijo _seconds para duraciones
- sufijo _bytes para tamaños
- labels con valores de baja cardinalidad (max 10-20 valores)
"""

from prometheus_client import Counter, Gauge, Histogram, Summary, REGISTRY, CollectorRegistry
from typing import Optional


class PrometheusMetrics:
    """
    Singleton para métricas de Prometheus.

    Todas las métricas se inicializan aquí para evitar re-registros
    y mantener un catálogo centralizado.
    """

    _instance: Optional['PrometheusMetrics'] = None

    def __new__(cls, registry: Optional[CollectorRegistry] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        # Evitar re-inicialización del singleton
        if self._initialized:
            return

        self._registry = registry or REGISTRY
        self._init_http_metrics()
        self._init_video_processing_metrics()
        self._init_celery_metrics()
        self._init_cache_metrics()
        self._init_scraping_metrics()
        self._init_distribution_metrics()
        self._init_system_metrics()

        self._initialized = True

    def _init_http_metrics(self):
        """Métricas de API HTTP."""

        self.http_requests_total = Counter(
            'http_requests_total',
            'Total de requests HTTP',
            ['method', 'endpoint', 'status'],
            registry=self._registry
        )

        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'Latencia de requests HTTP',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self._registry
        )

        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'Requests HTTP en progreso',
            ['method', 'endpoint'],
            registry=self._registry
        )

    def _init_video_processing_metrics(self):
        """Métricas del pipeline de procesamiento de videos."""

        # Videos procesados totales
        self.videos_processed_total = Counter(
            'videos_processed_total',
            'Total de videos procesados',
            ['status'],  # completed|failed
            registry=self._registry
        )

        # Duración de fases del procesamiento
        self.video_processing_duration_seconds = Histogram(
            'video_processing_duration_seconds',
            'Duración del procesamiento de videos por fase',
            ['phase'],  # download|transcription|summary|total
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0, 1800.0),
            registry=self._registry
        )

        # Duración de los videos procesados
        self.video_duration_seconds = Histogram(
            'video_duration_seconds',
            'Duración de los videos procesados',
            buckets=(60.0, 300.0, 600.0, 1200.0, 1800.0, 3600.0, 7200.0),
            registry=self._registry
        )

        # Errores de procesamiento
        self.video_processing_errors_total = Counter(
            'video_processing_errors_total',
            'Errores durante el procesamiento',
            ['error_type'],  # download|transcription|summary|other
            registry=self._registry
        )

        # Descarga de audio
        self.audio_downloads_total = Counter(
            'audio_downloads_total',
            'Total de descargas de audio',
            ['status'],  # success|failed
            registry=self._registry
        )

        self.audio_download_duration_seconds = Histogram(
            'audio_download_duration_seconds',
            'Duración de descarga de audio',
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
            registry=self._registry
        )

        self.audio_file_size_bytes = Histogram(
            'audio_file_size_bytes',
            'Tamaño de archivos de audio descargados',
            buckets=(1e6, 5e6, 10e6, 50e6, 100e6, 500e6, 1e9),  # 1MB a 1GB
            registry=self._registry
        )

        # Transcripción
        self.transcriptions_total = Counter(
            'transcriptions_total',
            'Total de transcripciones',
            ['model', 'status'],  # whisper-base/success|failed
            registry=self._registry
        )

        self.transcription_duration_seconds = Histogram(
            'transcription_duration_seconds',
            'Duración de transcripción',
            buckets=(5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0),
            registry=self._registry
        )

        self.transcription_text_length_chars = Histogram(
            'transcription_text_length_chars',
            'Longitud del texto transcrito',
            buckets=(1000, 5000, 10000, 50000, 100000, 500000),
            registry=self._registry
        )

        # Resúmenes
        self.summaries_generated_total = Counter(
            'summaries_generated_total',
            'Total de resúmenes generados',
            ['status'],  # success|failed
            registry=self._registry
        )

        self.summary_generation_duration_seconds = Histogram(
            'summary_generation_duration_seconds',
            'Duración de generación de resúmenes',
            buckets=(1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
            registry=self._registry
        )

        # API externa de IA (DeepSeek u otra)
        self.ai_api_calls_total = Counter(
            'ai_api_calls_total',
            'Llamadas a API de IA externa',
            ['provider', 'status'],  # deepseek/success|failed
            registry=self._registry
        )

        self.ai_tokens_used_total = Counter(
            'ai_tokens_used_total',
            'Tokens usados en API de IA',
            ['provider', 'type'],  # deepseek/input|output
            registry=self._registry
        )

        self.ai_api_cost_usd_total = Counter(
            'ai_api_cost_usd_total',
            'Costo acumulado de API de IA en USD',
            ['provider'],
            registry=self._registry
        )

    def _init_celery_metrics(self):
        """Métricas de Celery workers."""

        self.celery_task_total = Counter(
            'celery_task_total',
            'Total de tareas Celery',
            ['task_name', 'status'],  # success|failed|retry
            registry=self._registry
        )

        self.celery_task_duration_seconds = Histogram(
            'celery_task_duration_seconds',
            'Duración de tareas Celery',
            ['task_name'],
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0),
            registry=self._registry
        )

        self.celery_task_retries_total = Counter(
            'celery_task_retries_total',
            'Reintentos de tareas Celery',
            ['task_name'],
            registry=self._registry
        )

        self.celery_workers_active = Gauge(
            'celery_workers_active',
            'Workers Celery activos',
            registry=self._registry
        )

        self.celery_queue_length = Gauge(
            'celery_queue_length',
            'Longitud de cola Celery',
            ['queue_name'],  # scraping|video_processing|distribution
            registry=self._registry
        )

    def _init_cache_metrics(self):
        """Métricas de cache (Redis)."""

        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Hits de cache',
            ['cache_type'],  # summary|search|stats|other
            registry=self._registry
        )

        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Misses de cache',
            ['cache_type'],
            registry=self._registry
        )

        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Operaciones de cache',
            ['operation', 'status'],  # get|set|delete / success|failed
            registry=self._registry
        )

        self.cache_operation_duration_seconds = Histogram(
            'cache_operation_duration_seconds',
            'Duración de operaciones de cache',
            ['operation'],  # get|set|delete
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0),
            registry=self._registry
        )

        self.cache_value_size_bytes = Histogram(
            'cache_value_size_bytes',
            'Tamaño de valores en cache',
            ['cache_type'],
            buckets=(100, 1000, 10000, 100000, 1000000),
            registry=self._registry
        )

        self.cache_keys_total = Gauge(
            'cache_keys_total',
            'Total de claves en cache',
            ['cache_type'],
            registry=self._registry
        )

        # Métricas de Redis
        self.redis_memory_used_bytes = Gauge(
            'redis_memory_used_bytes',
            'Memoria usada por Redis',
            registry=self._registry
        )

        self.redis_connected_clients = Gauge(
            'redis_connected_clients',
            'Clientes conectados a Redis',
            registry=self._registry
        )

        self.cache_errors_total = Counter(
            'cache_errors_total',
            'Errores de cache',
            ['error_type'],
            registry=self._registry
        )

    def _init_scraping_metrics(self):
        """Métricas de scraping de fuentes."""

        self.scraping_runs_total = Counter(
            'scraping_runs_total',
            'Ejecuciones de scraping',
            ['status'],  # success|failed
            registry=self._registry
        )

        self.scraping_duration_seconds = Histogram(
            'scraping_duration_seconds',
            'Duración de scraping',
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
            registry=self._registry
        )

        self.videos_discovered_total = Counter(
            'videos_discovered_total',
            'Videos descubiertos en scraping',
            ['status'],  # new|existing
            registry=self._registry
        )

        self.sources_scraped_total = Counter(
            'sources_scraped_total',
            'Fuentes scrapeadas',
            ['status'],  # success|failed
            registry=self._registry
        )

    def _init_distribution_metrics(self):
        """Métricas de distribución (Telegram)."""

        self.summary_distributions_total = Counter(
            'summary_distributions_total',
            'Distribuciones de resúmenes',
            ['status'],  # success|failed
            registry=self._registry
        )

        self.distribution_duration_seconds = Histogram(
            'distribution_duration_seconds',
            'Duración de distribución',
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self._registry
        )

        self.telegram_messages_sent_total = Counter(
            'telegram_messages_sent_total',
            'Mensajes de Telegram enviados',
            ['status'],  # success|failed
            registry=self._registry
        )

        self.distribution_users_count = Gauge(
            'distribution_users_count',
            'Usuarios en distribución',
            ['type'],  # total|active|blocked
            registry=self._registry
        )

    def _init_system_metrics(self):
        """Métricas del sistema (recursos)."""

        self.system_cpu_usage_percent = Gauge(
            'system_cpu_usage_percent',
            'Uso de CPU del sistema',
            registry=self._registry
        )

        self.system_memory_used_bytes = Gauge(
            'system_memory_used_bytes',
            'Memoria usada del sistema',
            registry=self._registry
        )

        self.system_disk_used_bytes = Gauge(
            'system_disk_used_bytes',
            'Disco usado del sistema',
            ['mount_point'],
            registry=self._registry
        )

        # PostgreSQL
        self.postgres_connections_active = Gauge(
            'postgres_connections_active',
            'Conexiones activas a PostgreSQL',
            registry=self._registry
        )

        self.postgres_database_size_bytes = Gauge(
            'postgres_database_size_bytes',
            'Tamaño de la base de datos',
            registry=self._registry
        )

        self.postgres_query_duration_seconds = Histogram(
            'postgres_query_duration_seconds',
            'Duración de queries PostgreSQL',
            ['query_type'],  # select|insert|update|delete
            buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=self._registry
        )


# Singleton global
metrics = PrometheusMetrics()


def get_metrics() -> PrometheusMetrics:
    """
    Obtener la instancia global de métricas.

    Returns:
        PrometheusMetrics: Singleton de métricas
    """
    return metrics
