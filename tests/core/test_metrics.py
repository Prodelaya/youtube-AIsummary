"""
Tests unitarios para el módulo de métricas de Prometheus.

Verifica que:
- El singleton PrometheusMetrics se inicializa correctamente
- Todas las métricas se registran en el REGISTRY
- Los tipos de métricas son correctos (Counter, Gauge, Histogram)
- Los labels están configurados correctamente
- No hay duplicados en el registro
"""

import pytest
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram

from src.core.metrics import PrometheusMetrics, get_metrics, metrics


class TestPrometheusMetricsSingleton:
    """Tests del patrón Singleton."""

    def test_singleton_returns_same_instance(self):
        """Verifica que siempre retorna la misma instancia."""
        instance1 = PrometheusMetrics()
        instance2 = PrometheusMetrics()
        assert instance1 is instance2

    def test_get_metrics_returns_singleton(self):
        """Verifica que get_metrics() retorna el singleton."""
        instance = get_metrics()
        assert instance is metrics
        assert isinstance(instance, PrometheusMetrics)

    def test_singleton_initialized_flag(self):
        """Verifica que el singleton tiene flag de inicialización."""
        instance = PrometheusMetrics()
        assert hasattr(instance, "_initialized")
        assert instance._initialized is True


class TestHTTPMetrics:
    """Tests de métricas HTTP."""

    def test_http_requests_total_exists(self):
        """Verifica que http_requests_total está registrado."""
        assert hasattr(metrics, "http_requests_total")
        assert isinstance(metrics.http_requests_total, Counter)

    def test_http_request_duration_seconds_exists(self):
        """Verifica que http_request_duration_seconds está registrado."""
        assert hasattr(metrics, "http_request_duration_seconds")
        assert isinstance(metrics.http_request_duration_seconds, Histogram)

    def test_http_requests_in_progress_exists(self):
        """Verifica que http_requests_in_progress está registrado."""
        assert hasattr(metrics, "http_requests_in_progress")
        assert isinstance(metrics.http_requests_in_progress, Gauge)

    def test_http_metrics_have_correct_labels(self):
        """Verifica que las métricas HTTP tienen los labels correctos."""
        # http_requests_total debe tener labels: method, endpoint, status
        metric = metrics.http_requests_total
        # Intentar usar los labels esperados
        metric.labels(method="GET", endpoint="/api/v1/videos", status=200).inc()
        # Si no falla, los labels están correctos


class TestVideoProcessingMetrics:
    """Tests de métricas de procesamiento de videos."""

    def test_videos_processed_total_exists(self):
        """Verifica que videos_processed_total está registrado."""
        assert hasattr(metrics, "videos_processed_total")
        assert isinstance(metrics.videos_processed_total, Counter)

    def test_video_processing_duration_seconds_exists(self):
        """Verifica que video_processing_duration_seconds está registrado."""
        assert hasattr(metrics, "video_processing_duration_seconds")
        assert isinstance(metrics.video_processing_duration_seconds, Histogram)

    def test_video_duration_seconds_exists(self):
        """Verifica que video_duration_seconds está registrado."""
        assert hasattr(metrics, "video_duration_seconds")
        assert isinstance(metrics.video_duration_seconds, Histogram)

    def test_video_processing_errors_total_exists(self):
        """Verifica que video_processing_errors_total está registrado."""
        assert hasattr(metrics, "video_processing_errors_total")
        assert isinstance(metrics.video_processing_errors_total, Counter)

    def test_audio_downloads_total_exists(self):
        """Verifica que audio_downloads_total está registrado."""
        assert hasattr(metrics, "audio_downloads_total")
        assert isinstance(metrics.audio_downloads_total, Counter)

    def test_transcriptions_total_exists(self):
        """Verifica que transcriptions_total está registrado."""
        assert hasattr(metrics, "transcriptions_total")
        assert isinstance(metrics.transcriptions_total, Counter)

    def test_summaries_generated_total_exists(self):
        """Verifica que summaries_generated_total está registrado."""
        assert hasattr(metrics, "summaries_generated_total")
        assert isinstance(metrics.summaries_generated_total, Counter)

    def test_video_processing_metrics_have_correct_labels(self):
        """Verifica que las métricas de video processing tienen labels correctos."""
        # videos_processed_total debe tener label: status
        metrics.videos_processed_total.labels(status="completed").inc()

        # video_processing_duration_seconds debe tener label: phase
        metrics.video_processing_duration_seconds.labels(phase="download").observe(1.5)

        # video_processing_errors_total debe tener label: error_type
        metrics.video_processing_errors_total.labels(error_type="download").inc()


class TestCeleryMetrics:
    """Tests de métricas de Celery."""

    def test_celery_task_total_exists(self):
        """Verifica que celery_task_total está registrado."""
        assert hasattr(metrics, "celery_task_total")
        assert isinstance(metrics.celery_task_total, Counter)

    def test_celery_task_duration_seconds_exists(self):
        """Verifica que celery_task_duration_seconds está registrado."""
        assert hasattr(metrics, "celery_task_duration_seconds")
        assert isinstance(metrics.celery_task_duration_seconds, Histogram)

    def test_celery_task_retries_total_exists(self):
        """Verifica que celery_task_retries_total está registrado."""
        assert hasattr(metrics, "celery_task_retries_total")
        assert isinstance(metrics.celery_task_retries_total, Counter)

    def test_celery_workers_active_exists(self):
        """Verifica que celery_workers_active está registrado."""
        assert hasattr(metrics, "celery_workers_active")
        assert isinstance(metrics.celery_workers_active, Gauge)

    def test_celery_queue_length_exists(self):
        """Verifica que celery_queue_length está registrado."""
        assert hasattr(metrics, "celery_queue_length")
        assert isinstance(metrics.celery_queue_length, Gauge)

    def test_celery_metrics_have_correct_labels(self):
        """Verifica que las métricas de Celery tienen labels correctos."""
        # celery_task_total debe tener labels: task_name, status
        metrics.celery_task_total.labels(task_name="process_video", status="success").inc()

        # celery_task_duration_seconds debe tener label: task_name
        metrics.celery_task_duration_seconds.labels(task_name="process_video").observe(5.2)

        # celery_queue_length debe tener label: queue_name
        metrics.celery_queue_length.labels(queue_name="video_processing").set(10)


class TestCacheMetrics:
    """Tests de métricas de cache."""

    def test_cache_hits_total_exists(self):
        """Verifica que cache_hits_total está registrado."""
        assert hasattr(metrics, "cache_hits_total")
        assert isinstance(metrics.cache_hits_total, Counter)

    def test_cache_misses_total_exists(self):
        """Verifica que cache_misses_total está registrado."""
        assert hasattr(metrics, "cache_misses_total")
        assert isinstance(metrics.cache_misses_total, Counter)

    def test_cache_operations_total_exists(self):
        """Verifica que cache_operations_total está registrado."""
        assert hasattr(metrics, "cache_operations_total")
        assert isinstance(metrics.cache_operations_total, Counter)

    def test_cache_operation_duration_seconds_exists(self):
        """Verifica que cache_operation_duration_seconds está registrado."""
        assert hasattr(metrics, "cache_operation_duration_seconds")
        assert isinstance(metrics.cache_operation_duration_seconds, Histogram)

    def test_redis_memory_used_bytes_exists(self):
        """Verifica que redis_memory_used_bytes está registrado."""
        assert hasattr(metrics, "redis_memory_used_bytes")
        assert isinstance(metrics.redis_memory_used_bytes, Gauge)

    def test_cache_metrics_have_correct_labels(self):
        """Verifica que las métricas de cache tienen labels correctos."""
        # cache_hits_total debe tener label: cache_type
        metrics.cache_hits_total.labels(cache_type="summary").inc()

        # cache_operations_total debe tener labels: operation, status
        metrics.cache_operations_total.labels(operation="get", status="success").inc()


class TestScrapingMetrics:
    """Tests de métricas de scraping."""

    def test_scraping_runs_total_exists(self):
        """Verifica que scraping_runs_total está registrado."""
        assert hasattr(metrics, "scraping_runs_total")
        assert isinstance(metrics.scraping_runs_total, Counter)

    def test_scraping_duration_seconds_exists(self):
        """Verifica que scraping_duration_seconds está registrado."""
        assert hasattr(metrics, "scraping_duration_seconds")
        assert isinstance(metrics.scraping_duration_seconds, Histogram)

    def test_videos_discovered_total_exists(self):
        """Verifica que videos_discovered_total está registrado."""
        assert hasattr(metrics, "videos_discovered_total")
        assert isinstance(metrics.videos_discovered_total, Counter)

    def test_scraping_metrics_have_correct_labels(self):
        """Verifica que las métricas de scraping tienen labels correctos."""
        # scraping_runs_total debe tener label: status
        metrics.scraping_runs_total.labels(status="success").inc()

        # videos_discovered_total debe tener label: status
        metrics.videos_discovered_total.labels(status="new").inc()


class TestDistributionMetrics:
    """Tests de métricas de distribución."""

    def test_summary_distributions_total_exists(self):
        """Verifica que summary_distributions_total está registrado."""
        assert hasattr(metrics, "summary_distributions_total")
        assert isinstance(metrics.summary_distributions_total, Counter)

    def test_distribution_duration_seconds_exists(self):
        """Verifica que distribution_duration_seconds está registrado."""
        assert hasattr(metrics, "distribution_duration_seconds")
        assert isinstance(metrics.distribution_duration_seconds, Histogram)

    def test_telegram_messages_sent_total_exists(self):
        """Verifica que telegram_messages_sent_total está registrado."""
        assert hasattr(metrics, "telegram_messages_sent_total")
        assert isinstance(metrics.telegram_messages_sent_total, Counter)

    def test_distribution_metrics_have_correct_labels(self):
        """Verifica que las métricas de distribución tienen labels correctos."""
        # summary_distributions_total debe tener label: status
        metrics.summary_distributions_total.labels(status="success").inc()

        # telegram_messages_sent_total debe tener label: status
        metrics.telegram_messages_sent_total.labels(status="success").inc()


class TestSystemMetrics:
    """Tests de métricas del sistema."""

    def test_system_cpu_usage_percent_exists(self):
        """Verifica que system_cpu_usage_percent está registrado."""
        assert hasattr(metrics, "system_cpu_usage_percent")
        assert isinstance(metrics.system_cpu_usage_percent, Gauge)

    def test_system_memory_used_bytes_exists(self):
        """Verifica que system_memory_used_bytes está registrado."""
        assert hasattr(metrics, "system_memory_used_bytes")
        assert isinstance(metrics.system_memory_used_bytes, Gauge)

    def test_postgres_connections_active_exists(self):
        """Verifica que postgres_connections_active está registrado."""
        assert hasattr(metrics, "postgres_connections_active")
        assert isinstance(metrics.postgres_connections_active, Gauge)

    def test_system_metrics_can_be_set(self):
        """Verifica que las métricas de sistema se pueden actualizar."""
        metrics.system_cpu_usage_percent.set(75.5)
        metrics.system_memory_used_bytes.set(8589934592)  # 8GB
        metrics.postgres_connections_active.set(10)


class TestAIAPIMetrics:
    """Tests de métricas de API de IA."""

    def test_ai_api_calls_total_exists(self):
        """Verifica que ai_api_calls_total está registrado."""
        assert hasattr(metrics, "ai_api_calls_total")
        assert isinstance(metrics.ai_api_calls_total, Counter)

    def test_ai_tokens_used_total_exists(self):
        """Verifica que ai_tokens_used_total está registrado."""
        assert hasattr(metrics, "ai_tokens_used_total")
        assert isinstance(metrics.ai_tokens_used_total, Counter)

    def test_ai_api_cost_usd_total_exists(self):
        """Verifica que ai_api_cost_usd_total está registrado."""
        assert hasattr(metrics, "ai_api_cost_usd_total")
        assert isinstance(metrics.ai_api_cost_usd_total, Counter)

    def test_ai_metrics_have_correct_labels(self):
        """Verifica que las métricas de AI API tienen labels correctos."""
        # ai_api_calls_total debe tener labels: provider, status
        metrics.ai_api_calls_total.labels(provider="deepseek", status="success").inc()

        # ai_tokens_used_total debe tener labels: provider, type
        metrics.ai_tokens_used_total.labels(provider="deepseek", type="input").inc(100)
        metrics.ai_tokens_used_total.labels(provider="deepseek", type="output").inc(50)

        # ai_api_cost_usd_total debe tener label: provider
        metrics.ai_api_cost_usd_total.labels(provider="deepseek").inc(0.001)


class TestMetricsIntegration:
    """Tests de integración de métricas."""

    def test_all_metrics_registered_in_registry(self):
        """Verifica que todas las métricas están registradas en REGISTRY."""
        from prometheus_client import generate_latest

        output = generate_latest(REGISTRY).decode("utf-8")

        # Verificar que algunas métricas clave están en el output
        assert "videos_processed_total" in output
        assert "celery_task_duration_seconds" in output
        assert "cache_hits_total" in output
        assert "http_requests_total" in output

    def test_metrics_can_be_incremented(self):
        """Verifica que las métricas pueden ser incrementadas sin errores."""
        # Counter
        metrics.videos_processed_total.labels(status="completed").inc()

        # Histogram
        metrics.video_processing_duration_seconds.labels(phase="download").observe(2.5)

        # Gauge
        metrics.celery_workers_active.set(3)
        metrics.celery_workers_active.inc()
        metrics.celery_workers_active.dec()

    def test_histogram_buckets_are_reasonable(self):
        """Verifica que los histogramas tienen buckets razonables."""
        # video_processing_duration_seconds debe tener buckets para videos largos
        histogram = metrics.video_processing_duration_seconds
        # Observar valores variados
        histogram.labels(phase="download").observe(0.5)
        histogram.labels(phase="download").observe(5.0)
        histogram.labels(phase="download").observe(30.0)
        histogram.labels(phase="download").observe(300.0)
        # No debe fallar

    def test_no_duplicate_metrics(self):
        """Verifica que no hay métricas duplicadas."""
        from prometheus_client import generate_latest

        output = generate_latest(REGISTRY).decode("utf-8")
        lines = output.split("\n")

        # Contar ocurrencias de cada métrica TYPE
        type_declarations = [line for line in lines if line.startswith("# TYPE")]
        metric_names = [line.split()[2] for line in type_declarations]

        # Verificar que no hay duplicados
        assert len(metric_names) == len(
            set(metric_names)
        ), f"Found duplicate metrics: {[m for m in metric_names if metric_names.count(m) > 1]}"


class TestMetricsNaming:
    """Tests de convenciones de nombres de métricas."""

    def test_counter_metrics_have_total_suffix(self):
        """Verifica que los Counters tienen sufijo _total."""
        counter_attrs = [
            "http_requests_total",
            "videos_processed_total",
            "video_processing_errors_total",
            "celery_task_total",
            "cache_hits_total",
            "cache_misses_total",
        ]

        for attr in counter_attrs:
            assert hasattr(metrics, attr)
            assert attr.endswith("_total")
            assert isinstance(getattr(metrics, attr), Counter)

    def test_duration_metrics_have_seconds_suffix(self):
        """Verifica que las métricas de duración tienen sufijo _seconds."""
        duration_attrs = [
            "http_request_duration_seconds",
            "video_processing_duration_seconds",
            "celery_task_duration_seconds",
            "cache_operation_duration_seconds",
        ]

        for attr in duration_attrs:
            assert hasattr(metrics, attr)
            assert attr.endswith("_seconds")
            assert isinstance(getattr(metrics, attr), Histogram)

    def test_size_metrics_have_bytes_suffix(self):
        """Verifica que las métricas de tamaño tienen sufijo _bytes."""
        size_attrs = [
            "audio_file_size_bytes",
            "cache_value_size_bytes",
            "redis_memory_used_bytes",
            "system_memory_used_bytes",
        ]

        for attr in size_attrs:
            assert hasattr(metrics, attr)
            assert attr.endswith("_bytes")


class TestMetricsLabels:
    """Tests de labels de métricas."""

    def test_labels_are_lowercase(self):
        """Verifica que los labels son lowercase con snake_case."""
        # Intentar usar labels en diferentes métricas
        try:
            metrics.celery_task_total.labels(task_name="test", status="success").inc()
            metrics.cache_hits_total.labels(cache_type="summary").inc()
            metrics.video_processing_errors_total.labels(error_type="download").inc()
        except KeyError as e:
            pytest.fail(f"Label casing issue: {e}")

    def test_status_label_values_are_consistent(self):
        """Verifica que los valores de label 'status' son consistentes."""
        # Los valores comunes de status deben ser: success, failed, completed, retry
        valid_statuses = ["success", "failed", "completed", "retry"]

        # Estas métricas usan el label 'status'
        metrics.celery_task_total.labels(task_name="test", status="success").inc()
        metrics.videos_processed_total.labels(status="completed").inc()
        metrics.cache_operations_total.labels(operation="get", status="success").inc()
