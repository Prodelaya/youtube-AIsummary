"""Tests de integracion para Videos API."""



class TestVideosAPI:
    """Tests para endpoints de videos."""

    def test_list_videos_without_auth(self, client):
        """Test que GET /videos funciona sin autenticacion."""
        response = client.get("/api/v1/videos")
        assert response.status_code == 200

    def test_list_videos_success(self, client, multiple_videos):
        """Test listar videos."""
        response = client.get("/api/v1/videos")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "cursor" in data
        assert len(data["data"]) > 0

    def test_get_video_by_id(self, client, sample_video):
        """Test obtener video por ID."""
        response = client.get(f"/api/v1/videos/{sample_video.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_video.id)
        assert data["youtube_id"] == sample_video.youtube_id

    def test_get_video_not_found(self, client):
        """Test video inexistente retorna 404."""
        from uuid import uuid4

        fake_id = uuid4()
        response = client.get(f"/api/v1/videos/{fake_id}")
        assert response.status_code == 404

    def test_create_video_without_auth(self, client, sample_source):
        """Test que crear video sin autenticacion funciona."""
        payload = {
            "source_id": str(sample_source.id),
            "youtube_id": "dQw4w9WgXcQ",  # 11 caracteres (YouTube ID valido)
            "title": "New Video",
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "duration_seconds": 300,
        }
        response = client.post("/api/v1/videos", json=payload)
        assert response.status_code == 201

    def test_create_video_success(self, client, sample_source):
        """Test crear video."""
        payload = {
            "source_id": str(sample_source.id),
            "youtube_id": "xvFZjo5PgG0",  # 11 caracteres (YouTube ID valido)
            "title": "New Video",
            "url": "https://youtube.com/watch?v=xvFZjo5PgG0",
            "duration_seconds": 300,
        }
        response = client.post("/api/v1/videos", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["youtube_id"] == "xvFZjo5PgG0"

    def test_list_videos_with_filters(self, client, multiple_videos):
        """Test listar videos con filtros."""
        response = client.get("/api/v1/videos?status=pending")
        assert response.status_code == 200

    def test_list_videos_pagination(self, client, multiple_videos):
        """Test paginacion de videos."""
        response = client.get("/api/v1/videos?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) <= 5
