"""
Tests for the Auth microservice.
Covers: /login, /validate, /health endpoints.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import os

# Set environment variables before importing server
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_USER", "test")
os.environ.setdefault("MYSQL_PASSWORD", "test")
os.environ.setdefault("MYSQL_DB", "test")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("JWT_SECRET", "test-secret")


@pytest.fixture
def client():
    """Create Flask test client with mocked MySQL."""
    with patch("flask_mysqldb.MySQL"):
        from server import server
        server.config["TESTING"] = True
        with server.test_client() as client:
            yield client


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200_when_db_connected(self, client):
        with patch("server.mysql") as mock_mysql:
            mock_cursor = MagicMock()
            mock_mysql.connection.cursor.return_value = mock_cursor
            response = client.get("/health")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "healthy"
            assert data["service"] == "auth"
            assert data["checks"]["mysql"] == "connected"

    def test_health_returns_503_when_db_down(self, client):
        with patch("server.mysql") as mock_mysql:
            mock_mysql.connection.cursor.side_effect = Exception("Connection refused")
            response = client.get("/health")
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data["status"] == "unhealthy"


class TestLoginEndpoint:
    """Tests for /login endpoint."""

    def test_login_missing_credentials(self, client):
        response = client.post("/login")
        assert response.status_code == 401

    def test_login_invalid_credentials(self, client):
        with patch("server.mysql") as mock_mysql:
            mock_cursor = MagicMock()
            mock_cursor.execute.return_value = 0
            mock_mysql.connection.cursor.return_value = mock_cursor
            response = client.post(
                "/login",
                headers={"Authorization": "Basic dGVzdEB0ZXN0LmNvbTp3cm9uZw=="}
            )
            assert response.status_code == 401

    def test_login_success_returns_jwt(self, client):
        with patch("server.mysql") as mock_mysql:
            mock_cursor = MagicMock()
            mock_cursor.execute.return_value = 1
            mock_cursor.fetchone.return_value = ("test@test.com", "password123")
            mock_mysql.connection.cursor.return_value = mock_cursor
            response = client.post(
                "/login",
                headers={"Authorization": "Basic dGVzdEB0ZXN0LmNvbTpwYXNzd29yZDEyMw=="}
            )
            assert response.status_code == 200


class TestValidateEndpoint:
    """Tests for /validate endpoint."""

    def test_validate_missing_token(self, client):
        response = client.post("/validate")
        assert response.status_code in [400, 401, 500]

    def test_validate_invalid_token(self, client):
        response = client.post(
            "/validate",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 403
