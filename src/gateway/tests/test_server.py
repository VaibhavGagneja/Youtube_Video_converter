"""
Tests for the Gateway microservice.
Covers: /health, /login, /upload, /download endpoints.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


@pytest.fixture
def client():
    """Create Flask test client with mocked dependencies."""
    with patch("flask_pymongo.PyMongo"), \
         patch("gridfs.GridFS"), \
         patch("pika.BlockingConnection") as mock_pika:
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_pika.return_value = mock_conn

        from server import server
        server.config["TESTING"] = True
        with server.test_client() as client:
            yield client


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client):
        with patch("server.mongo_video") as mock_mongo, \
             patch("server.connection") as mock_conn:
            mock_mongo.db.command.return_value = {"ok": 1}
            mock_conn.is_open = True
            response = client.get("/health")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "healthy"
            assert data["checks"]["mongodb"] == "connected"
            assert data["checks"]["rabbitmq"] == "connected"

    def test_health_503_when_mongo_down(self, client):
        with patch("server.mongo_video") as mock_mongo, \
             patch("server.connection") as mock_conn:
            mock_mongo.db.command.side_effect = Exception("Connection refused")
            mock_conn.is_open = True
            response = client.get("/health")
            assert response.status_code == 503


class TestLoginEndpoint:
    """Tests for /login endpoint."""

    def test_login_proxies_to_auth_service(self, client):
        with patch("auth_svc.access.login") as mock_login:
            mock_login.return_value = ("fake-jwt-token", None)
            response = client.post("/login")
            assert response.status_code == 200


class TestUploadEndpoint:
    """Tests for /upload endpoint."""

    def test_upload_requires_auth(self, client):
        with patch("auth.validate.token") as mock_validate:
            mock_validate.return_value = (None, ("not authorized", 401))
            response = client.post("/upload")
            assert response.status_code == 401

    def test_upload_requires_admin(self, client):
        with patch("auth.validate.token") as mock_validate:
            mock_validate.return_value = (json.dumps({"admin": False, "username": "user"}), None)
            data = {"file": (BytesIO(b"test"), "test.mp4")}
            response = client.post(
                "/upload",
                data=data,
                content_type="multipart/form-data"
            )
            assert response.status_code == 401

    def test_upload_requires_exactly_one_file(self, client):
        with patch("auth.validate.token") as mock_validate:
            mock_validate.return_value = (json.dumps({"admin": True, "username": "admin"}), None)
            response = client.post("/upload")
            assert response.status_code == 400


class TestDownloadEndpoint:
    """Tests for /download endpoint."""

    def test_download_requires_auth(self, client):
        with patch("auth.validate.token") as mock_validate:
            mock_validate.return_value = (None, ("not authorized", 401))
            response = client.get("/download?fid=123")
            assert response.status_code == 401

    def test_download_requires_fid(self, client):
        with patch("auth.validate.token") as mock_validate:
            mock_validate.return_value = (json.dumps({"admin": True, "username": "admin"}), None)
            response = client.get("/download")
            assert response.status_code == 400
