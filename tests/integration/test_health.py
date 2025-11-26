"""
Tests de integracion para Health Check endpoint.

Tests basicos que verifican:
- Endpoint /health esta disponible
- Retorna status code 200
- Retorna estructura JSON correcta
"""


class TestHealthEndpoint:
    """Tests para el endpoint de health check."""

    def test_health_check_returns_200(self, client):
        """Test que health check retorna 200 OK."""
        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200

    def test_health_check_returns_json(self, client):
        """Test que health check retorna JSON valido."""
        # Act
        response = client.get("/health")

        # Assert
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)

    def test_health_check_has_status_field(self, client):
        """Test que health check tiene campo 'status'."""
        # Act
        response = client.get("/health")
        data = response.json()

        # Assert
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
