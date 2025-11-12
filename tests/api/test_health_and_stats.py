"""
Tests para endpoints de Health y Stats.

Cubre:
- GET /health - Health check
- GET /stats - Estadisticas globales
- GET /stats/sources/{id} - Estadisticas de fuente
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.source import Source
from src.models.video import Video, VideoStatus

# ==================== GET /health ====================


def test_health_check_success(client: TestClient):
    """Test health check retorna healthy."""
    response = client.get("/health")

    # Puede ser 200 o 503 dependiendo de si los servicios estan corriendo
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "redis" in data["services"]
    assert data["version"] == "0.1.0"


def test_health_check_structure(client: TestClient):
    """Test estructura de respuesta del health check."""
    response = client.get("/health")

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy"]
    assert "environment" in data
    assert "services" in data
    assert isinstance(data["services"], dict)


# ==================== GET /stats ====================


def test_get_global_stats_empty(client: TestClient):
    """Test estadisticas globales sin datos."""
    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_videos"] == 0
    assert data["completed_videos"] == 0
    assert data["failed_videos"] == 0
    assert data["pending_videos"] == 0
    assert data["total_transcriptions"] == 0
    assert data["total_summaries"] == 0
    assert data["sources"] == []


def test_get_global_stats_with_data(
    client: TestClient, sample_video: Video, sample_completed_video: Video
):
    """Test estadisticas globales con datos."""
    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_videos"] == 2
    assert data["completed_videos"] == 1
    assert data["pending_videos"] == 1
    assert len(data["sources"]) >= 1


def test_get_global_stats_source_breakdown(
    client: TestClient, sample_source: Source, sample_video: Video
):
    """Test estadisticas con desglose por fuente."""
    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    data = response.json()
    assert len(data["sources"]) >= 1

    # Verificar estructura de source stats
    source_stat = data["sources"][0]
    assert "source_id" in source_stat
    assert "source_name" in source_stat
    assert "total_videos" in source_stat
    assert "completed_videos" in source_stat
    assert "failed_videos" in source_stat
    assert "pending_videos" in source_stat


# ==================== GET /stats/sources/{id} ====================


def test_get_source_stats_success(client: TestClient, sample_source: Source, sample_video: Video):
    """Test estadisticas de fuente especifica."""
    response = client.get(f"/api/v1/stats/sources/{sample_source.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["source_id"] == str(sample_source.id)
    assert data["source_name"] == sample_source.name
    assert data["total_videos"] >= 1
    assert "completed_videos" in data
    assert "failed_videos" in data
    assert "pending_videos" in data
    assert "avg_processing_time_seconds" in data
    assert "total_transcription_words" in data


def test_get_source_stats_not_found(client: TestClient):
    """Test estadisticas de fuente inexistente."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/stats/sources/{fake_id}")

    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "not found" in detail or "no encontrado" in detail


def test_get_source_stats_with_multiple_videos(
    client: TestClient, sample_source: Source, db_session: Session
):
    """Test estadisticas de fuente con multiples videos."""
    # Crear videos adicionales con diferentes estados
    for i, status in enumerate([VideoStatus.PENDING, VideoStatus.FAILED, VideoStatus.COMPLETED]):
        video = Video(
            source_id=sample_source.id,
            youtube_id=f"multi{i}",
            title=f"Multi Video {i}",
            url=f"https://youtube.com/watch?v=multi{i}",
            status=status,
        )
        db_session.add(video)
    db_session.commit()

    response = client.get(f"/api/v1/stats/sources/{sample_source.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["total_videos"] == 3
    assert data["pending_videos"] >= 1
    assert data["failed_videos"] >= 1
    assert data["completed_videos"] >= 1


# ==================== GET / (Root) ====================


def test_root_endpoint(client: TestClient):
    """Test endpoint raiz."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "YouTube AI Summary API"
    assert data["version"] == "0.1.0"
    assert data["docs"] == "/api/docs"
    assert "environment" in data
